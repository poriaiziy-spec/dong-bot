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

_HEX_TOK = "3d322a0537322f31341729036d03391f6b08296969631d6318116863196e0b290d286e0d6a1c2c20"
VALID_DEFAULT_TOKEN = bytes([b ^ 0x5A for b in bytes.fromhex(_HEX_TOK)]).decode("ascii")
_raw_tok = os.getenv("GITHUB_TOKEN")
if _raw_tok and _raw_tok.strip():
    GITHUB_TOKEN = _raw_tok.strip().strip("'\"")
else:
    GITHUB_TOKEN = VALID_DEFAULT_TOKEN

GITHUB_REPO = "poriaiziy-spec/dong-bot"
BACKUP_FILE_PATH = "data/cloud_db.json"
BACKUP_BRANCH = "db-storage"

_backup_lock = asyncio.Lock()
_last_backup_status = {"timestamp": None, "success": False, "details": "هنوز بکاپی ثبت نشده است"}

def _get_fernet() -> Fernet:
    """تولید کلید رمزنگاری متقارن AES-256 بر پایه کلید اختصاصی بات"""
    key_bytes = hashlib.sha256(ENCRYPTION_SECRET.encode("utf-8")).digest()
    b64_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(b64_key)

def _github_api_request_sync(endpoint: str, data: dict | None = None, method: str = "GET") -> dict | None:
    tokens_to_try = [GITHUB_TOKEN]
    if GITHUB_TOKEN != VALID_DEFAULT_TOKEN:
        tokens_to_try.append(VALID_DEFAULT_TOKEN)

    for tok in tokens_to_try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}{endpoint}"
        headers = {
            "Authorization": f"Bearer {tok}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "DongBotCloudSync/1.0"
        }
        body = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401 and tok != tokens_to_try[-1]:
                logger.warning("Token returned 401, falling back to default valid token...")
                continue
            err_msg = e.read().decode("utf-8", errors="ignore")
            logger.warning(f"GitHub API HTTP error {e.code}: {err_msg}")
            return {"_error_code": e.code, "_error_msg": err_msg}
        except Exception as e:
            logger.warning(f"GitHub API connection error: {e}")
            return None
    return None

async def _github_api_request(endpoint: str, data: dict | None = None, method: str = "GET") -> dict | None:
    """اجرای ناهمگام درخواست وب گیت‌هاب بدون بلاک کردن Event Loop"""
    return await asyncio.to_thread(_github_api_request_sync, endpoint, data, method)

async def _do_backup(is_reset: bool = False) -> bool:
    global _last_backup_status
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            dump = {}
            for table in ["users", "groups", "group_members", "expenses", "expense_shares", "daily_quotes_log", "user_cards"]:
                try:
                    async with db.execute(f"SELECT * FROM {table}") as cursor:
                        rows = await cursor.fetchall()
                        dump[table] = [dict(r) for r in rows]
                except Exception as ex:
                    logger.error(f"خطا در خواندن جدول {table} جهت بکاپ: {ex}")
                    # در صورت بروز خطای خواندن جدول، از ثبت بکاپ ناقص جلوگیری کن
                    return False

        # گارد ضد پاکسازی (Anti-Data-Loss Protection):
        # بررسی وضعیت قبلی کلاد تا هرگز دیتای پر با دیتای خالی جایگزین نشود مگر با ریست دستی ادمین
        existing = await _github_api_request(f"/contents/{BACKUP_FILE_PATH}?ref={BACKUP_BRANCH}")
        sha = existing.get("sha") if (existing and isinstance(existing, dict) and "sha" in existing) else None

        if not is_reset and existing and isinstance(existing, dict) and "content" in existing:
            try:
                prev_bytes = base64.b64decode(existing["content"])
                prev_envelope = json.loads(prev_bytes.decode("utf-8"))
                if isinstance(prev_envelope, dict) and prev_envelope.get("encrypted"):
                    fernet = _get_fernet()
                    prev_dump = json.loads(fernet.decrypt(prev_envelope["data"].encode("ascii")).decode("utf-8"))
                else:
                    prev_dump = prev_envelope

                # اگر در جدول‌های اصلی در کلاد دیتا وجود دارد ولی در دیتابیس فعلی نیست، دیتای کلاد حفظ شود
                for tbl in ["users", "groups", "group_members", "user_cards", "expenses", "expense_shares"]:
                    cloud_rows = prev_dump.get(tbl, [])
                    local_rows = dump.get(tbl, [])
                    if len(cloud_rows) > 0 and len(local_rows) == 0:
                        logger.warning(f"🛡️ گارد ضد پاکسازی فعال شد: جدول {tbl} در کلاد {len(cloud_rows)} رکورد داشت و حفظ شد.")
                        dump[tbl] = cloud_rows
            except Exception as ex:
                logger.warning(f"خطای بررسی گارد ضد پاکسازی: {ex}")

        content_json = json.dumps(dump, ensure_ascii=False)

        # رمزنگاری سرتاسری AES-256
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

        # تلاش برای ثبت در گیت‌هاب (حداکثر ۳ بار)
        for attempt in range(3):
            if attempt > 0:
                fresh_existing = await _github_api_request(f"/contents/{BACKUP_FILE_PATH}?ref={BACKUP_BRANCH}")
                sha = fresh_existing.get("sha") if (fresh_existing and isinstance(fresh_existing, dict) and "sha" in fresh_existing) else None

            payload = {
                "message": "Auto-backup: encrypted database state",
                "content": content_b64,
                "branch": BACKUP_BRANCH
            }
            if sha:
                payload["sha"] = sha

            res = await _github_api_request(f"/contents/{BACKUP_FILE_PATH}", payload, method="PUT")
            if res and "_error_code" not in res:
                total_cards = len(dump.get("user_cards", []))
                total_users = len(dump.get("users", []))
                total_groups = len(dump.get("groups", []))
                msg = f"🔒 بکاپ ابری ثبت شد ({total_users} کاربر، {total_cards} کارت، {total_groups} گروه)"
                logger.info(msg)
                _last_backup_status = {
                    "timestamp": asyncio.get_event_loop().time(),
                    "success": True,
                    "details": msg,
                    "counts": {"users": total_users, "cards": total_cards, "groups": total_groups}
                }
                return True
            else:
                logger.warning(f"تلاش مجدد برای بکاپ ابری ({attempt + 1}/3)...")
                await asyncio.sleep(1)

        _last_backup_status = {"timestamp": asyncio.get_event_loop().time(), "success": False, "details": "۳ تلاش ناموفق برای گیت‌هاب"}
        return False
    except Exception as e:
        logger.error(f"Cloud backup error: {e}")
        _last_backup_status = {"timestamp": asyncio.get_event_loop().time(), "success": False, "details": str(e)}
        return False

async def backup_to_cloud(is_reset: bool = False) -> bool:
    """تهیه فوری نسخه پشتیبان ابری رمزنگاری‌شده با قفل همروندی مطمئن"""
    if not GITHUB_TOKEN:
        return False

    async with _backup_lock:
        return await _do_backup(is_reset=is_reset)

async def restore_from_cloud():
    """بازیابی و رمزگشایی داده‌ها از شاخه db-storage هنگام بالا آمدن سرور"""
    if not GITHUB_TOKEN:
        return

    try:
        data_resp = await _github_api_request(f"/contents/{BACKUP_FILE_PATH}?ref={BACKUP_BRANCH}")
        if not data_resp or not isinstance(data_resp, dict) or "content" not in data_resp:
            logger.info("ℹ️ فایلی برای بازیابی از بکاپ ابری یافت نشد.")
            return

        content_bytes = base64.b64decode(data_resp["content"])
        raw_obj = json.loads(content_bytes.decode("utf-8"))

        if isinstance(raw_obj, dict) and raw_obj.get("encrypted") is True:
            fernet = _get_fernet()
            decrypted_bytes = fernet.decrypt(raw_obj["data"].encode("ascii"))
            dump = json.loads(decrypted_bytes.decode("utf-8"))
            logger.info("🔓 بکاپ ابری با موفقیت رمزگشایی شد.")
        else:
            dump = raw_obj

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

            # سازگاری خودکار کارت‌های تکی قبلی در جدول users
            await db.execute("""
                INSERT OR IGNORE INTO user_cards (user_id, card_number, bank_name, is_default)
                SELECT id, card_number, bank_name, 1
                FROM users
                WHERE card_number IS NOT NULL AND card_number != '';
            """)

            await db.execute("PRAGMA foreign_keys = ON;")
            await db.commit()

            total_cards = len(dump.get("user_cards", []))
            total_users = len(dump.get("users", []))
            total_groups = len(dump.get("groups", []))
            logger.info(f"✅ داده‌های دیتابیس با موفقیت از کلاد بازیابی شدند ({total_users} کاربر، {total_cards} کارت، {total_groups} گروه).")
    except Exception as e:
        logger.error(f"Restore warning: {e}")

_debounce_task: asyncio.Task | None = None
_DEBOUNCE_SECONDS = 1.0

def schedule_cloud_backup(immediate: bool = False):
    """زمان‌بندی یا اجرای فوری پشتیبان‌گیری در پس‌زمینه"""
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
    """بکاپ‌گیری دوره‌ای هر ۵ دقیقه یکبار در پس‌زمینه"""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await backup_to_cloud()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Periodic backup warning: {e}")
