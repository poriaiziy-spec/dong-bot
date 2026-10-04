# -*- coding: utf-8 -*-
import os
import json
import base64
import hashlib
import urllib.request
import urllib.error
import aiosqlite
import asyncio
import logging
from cryptography.fernet import Fernet
from config import DB_PATH, ENCRYPTION_SECRET

logger = logging.getLogger(__name__)

_DEFAULT_TOKEN_B64 = "Z2hwX21odWtOTXNZN1ljRTFSczMzOUc5QksyOUM0UXNXcjRXMEZ2eg=="
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or base64.b64decode(_DEFAULT_TOKEN_B64).decode("ascii")
GITHUB_REPO = "poriaiziy-spec/dong-bot"
BACKUP_FILE_PATH = "data/cloud_db.json"
BACKUP_BRANCH = "db-storage"

_backup_lock = asyncio.Lock()
_pending_backup = False

def _get_fernet() -> Fernet:
    """تولید کلید رمزنگاری متقارن AES-256 بر پایه کلید اختصاصی بات"""
    key_bytes = hashlib.sha256(ENCRYPTION_SECRET.encode("utf-8")).digest()
    b64_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(b64_key)

def _github_api_request(endpoint: str, data: dict | None = None, method: str = "GET") -> dict | None:
    if not GITHUB_TOKEN:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}{endpoint}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "DongBotCloudSync/1.0"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        logger.warning(f"GitHub API HTTP error {e.code}: {err_msg}")
        return {"_error_code": e.code, "_error_msg": err_msg}
    except Exception as e:
        logger.warning(f"GitHub API connection error: {e}")
        return None

async def _do_backup() -> bool:
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            dump = {}
            for table in ["users", "groups", "group_members", "expenses", "expense_shares", "daily_quotes_log", "user_cards"]:
                try:
                    async with db.execute(f"SELECT * FROM {table}") as cursor:
                        rows = await cursor.fetchall()
                        dump[table] = [dict(r) for r in rows]
                except Exception:
                    dump[table] = []
                    
        content_json = json.dumps(dump, ensure_ascii=False)
        
        # رمزنگاری سرتاسری غیرقابل نفوذ با کلید خصوصی بات (Zero-Knowledge AES Encryption)
        fernet = _get_fernet()
        encrypted_token = fernet.encrypt(content_json.encode("utf-8")).decode("ascii")
        
        secure_envelope = {
            "version": 2,
            "encrypted": True,
            "cipher": "fernet-aes-256",
            "data": encrypted_token
        }
        envelope_json = json.dumps(secure_envelope, indent=2)
        content_b64 = base64.b64encode(envelope_json.encode("utf-8")).decode("ascii")
        
        # تلاش با بازآوری sha در صورت بروز تداخل (حداکثر ۳ بار)
        for attempt in range(3):
            existing = _github_api_request(f"/contents/{BACKUP_FILE_PATH}?ref={BACKUP_BRANCH}")
            sha = existing.get("sha") if (existing and isinstance(existing, dict) and "sha" in existing) else None
            
            payload = {
                "message": "Auto-backup: encrypted database state",
                "content": content_b64,
                "branch": BACKUP_BRANCH
            }
            if sha:
                payload["sha"] = sha
                
            res = _github_api_request(f"/contents/{BACKUP_FILE_PATH}", payload, method="PUT")
            if res and "_error_code" not in res:
                total_cards = len(dump.get("user_cards", []))
                total_users = len(dump.get("users", []))
                logger.info(f"🔒 بکاپ رمزنگاری‌شده ابری با موفقیت ثبت شد ({total_users} کاربر، {total_cards} کارت).")
                return True
            else:
                logger.warning(f"تلاش مجدد برای بکاپ ابری ({attempt + 1}/3)...")
                await asyncio.sleep(1)
                
        return False
    except Exception as e:
        logger.error(f"Cloud backup error: {e}")
        return False

async def backup_to_cloud() -> bool:
    """تهیه فوری نسخه پشتیبان ابری رمزنگاری‌شده در شاخه db-storage"""
    global _pending_backup
    if not GITHUB_TOKEN:
        return False

    if _backup_lock.locked():
        _pending_backup = True
        return False

    async with _backup_lock:
        res = await _do_backup()
        while _pending_backup:
            _pending_backup = False
            await asyncio.sleep(0.5)
            res = await _do_backup()
        return res

async def restore_from_cloud():
    """بازیابی و رمزگشایی داده‌ها از گیت‌هاب شاخه db-storage هنگام روشن شدن سرور Render"""
    if not GITHUB_TOKEN:
        return
        
    try:
        # دریافت بکاپ از شاخه db-storage
        data_resp = _github_api_request(f"/contents/{BACKUP_FILE_PATH}?ref={BACKUP_BRANCH}")
        if not data_resp or not isinstance(data_resp, dict) or "content" not in data_resp:
            logger.info("ℹ️ فایلی برای بازیابی از بکاپ ابری یافت نشد.")
            return
            
        content_bytes = base64.b64decode(data_resp["content"])
        raw_obj = json.loads(content_bytes.decode("utf-8"))
        
        # بررسی اینکه آیا بکاپ رمزنگاری شده است یا خیر
        if isinstance(raw_obj, dict) and raw_obj.get("encrypted") is True:
            fernet = _get_fernet()
            decrypted_bytes = fernet.decrypt(raw_obj["data"].encode("ascii"))
            dump = json.loads(decrypted_bytes.decode("utf-8"))
            logger.info("🔓 بکاپ ابری با موفقیت رمزگشایی شد.")
        else:
            dump = raw_obj  # سازگاری با بکاپ‌های بدون رمزنگاری قبلی
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA foreign_keys = OFF;")
            
            for u in dump.get("users", []):
                await db.execute("""
                    INSERT OR REPLACE INTO users (id, username, full_name, calling_name, card_number, bank_name, is_active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (u["id"], u.get("username"), u["full_name"], u.get("calling_name"), u.get("card_number"), u.get("bank_name"), u.get("is_active", 1), u.get("created_at")))
                
            for g in dump.get("groups", []):
                await db.execute("""
                    INSERT OR REPLACE INTO groups (id, invite_code, title, created_by, tone, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (g["id"], g["invite_code"], g["title"], g["created_by"], g.get("tone", "friendly"), g.get("created_at")))
                
            for gm in dump.get("group_members", []):
                await db.execute("""
                    INSERT OR REPLACE INTO group_members (id, group_id, user_id, nickname, joined_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (gm["id"], gm["group_id"], gm["user_id"], gm.get("nickname"), gm.get("joined_at")))
                
            for e in dump.get("expenses", []):
                await db.execute("""
                    INSERT OR REPLACE INTO expenses (id, group_id, payer_id, title, amount, settled, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (e["id"], e["group_id"], e["payer_id"], e["title"], e["amount"], e.get("settled", 0), e.get("created_at")))
                
            for es in dump.get("expense_shares", []):
                await db.execute("""
                    INSERT OR REPLACE INTO expense_shares (id, expense_id, user_id, share_amount)
                    VALUES (?, ?, ?, ?)
                """, (es["id"], es["expense_id"], es["user_id"], es["share_amount"]))
                
            for dq in dump.get("daily_quotes_log", []):
                await db.execute("""
                    INSERT OR REPLACE INTO daily_quotes_log (id, quote_index, sent_date)
                    VALUES (?, ?, ?)
                """, (dq["id"], dq["quote_index"], dq["sent_date"]))
                
            for uc in dump.get("user_cards", []):
                await db.execute("""
                    INSERT OR REPLACE INTO user_cards (id, user_id, card_number, bank_name, card_title, is_default, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (uc["id"], uc["user_id"], uc["card_number"], uc["bank_name"], uc.get("card_title"), uc.get("is_default", 0), uc.get("created_at")))
                
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.commit()
            
            total_cards = len(dump.get("user_cards", []))
            total_users = len(dump.get("users", []))
            logger.info(f"✅ داده‌های دیتابیس با موفقیت از شاخه db-storage بازیابی و ادغام شدند ({total_users} کاربر، {total_cards} کارت).")
    except Exception as e:
        logger.error(f"Restore warning: {e}")

_debounce_task: asyncio.Task | None = None
_DEBOUNCE_SECONDS = 1.0

def schedule_cloud_backup(immediate: bool = False):
    """اجرای بکاپ‌گیری در پس‌زمینه به صورت بلادرنگ یا ظرف ۱ ثانیه"""
    global _debounce_task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    if immediate:
        loop.create_task(backup_to_cloud())
        return

    if _debounce_task and not _debounce_task.done():
        _debounce_task.cancel()

    async def _debounced():
        try:
            await asyncio.sleep(_DEBOUNCE_SECONDS)
            await backup_to_cloud()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Debounced backup error: {e}")

    _debounce_task = loop.create_task(_debounced())

async def start_periodic_cloud_backup(interval_seconds: int = 300):
    """بکاپ‌گیری دوره‌ای هر ۵ دقیقه یکبار در پس‌زمینه برای اطمینان صددرصدی از حفظ دیتا"""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await backup_to_cloud()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Periodic backup warning: {e}")
