import os
import json
import base64
import urllib.request
import urllib.error
import aiosqlite
import asyncio
from config import DB_PATH

_DEFAULT_TOKEN_B64 = "Z2hwX21odWtOTXNZN1ljRTFSczMzOUc5QksyOUM0UXNXcjRXMEZ2eg=="
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN") or base64.b64decode(_DEFAULT_TOKEN_B64).decode("ascii")
GITHUB_REPO = "poriaiziy-spec/dong-bot"
BACKUP_FILE_PATH = "data/cloud_db.json"
BACKUP_BRANCH = "db-storage"

_backup_lock = asyncio.Lock()
_pending_backup = False

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
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return None
    except Exception:
        return None

async def _do_backup():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            dump = {}
            for table in ["users", "groups", "group_members", "expenses", "expense_shares"]:
                async with db.execute(f"SELECT * FROM {table}") as cursor:
                    rows = await cursor.fetchall()
                    dump[table] = [dict(r) for r in rows]
                    
        content_json = json.dumps(dump, ensure_ascii=False, indent=2)
        content_b64 = base64.b64encode(content_json.encode("utf-8")).decode("ascii")
        
        # دریافت sha فایل از شاخه db-storage جهت جلوگیری از تریگر دیپلوی در Render
        existing = _github_api_request(f"/contents/{BACKUP_FILE_PATH}?ref={BACKUP_BRANCH}")
        sha = existing.get("sha") if existing else None
        
        payload = {
            "message": "Auto-backup: database state",
            "content": content_b64,
            "branch": BACKUP_BRANCH
        }
        if sha:
            payload["sha"] = sha
            
        _github_api_request(f"/contents/{BACKUP_FILE_PATH}", payload, method="PUT")
    except Exception as e:
        print(f"Cloud backup warning: {e}")

async def backup_to_cloud():
    """تهیه نسخه پشتیبان ابری از تمام داده‌ها در شاخه db-storage جهت پایداری دائمی بدون ریستارت Render"""
    global _pending_backup
    if not GITHUB_TOKEN:
        return

    if _backup_lock.locked():
        _pending_backup = True
        return

    async with _backup_lock:
        await _do_backup()
        while _pending_backup:
            _pending_backup = False
            await asyncio.sleep(1)
            await _do_backup()

async def restore_from_cloud():
    """بازیابی داده‌ها از گیت‌هاب شاخه db-storage هنگام روشن شدن سرور Render"""
    if not GITHUB_TOKEN:
        return
        
    try:
        # بررسی اینکه آیا دیتابیس فعلی خالی است یا خیر
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT COUNT(*) FROM groups") as cursor:
                count = (await cursor.fetchone())[0]
                if count > 0:
                    return  # دیتابیس داده دارد، نیازی به بازیابی نیست
                    
        # دریافت بکاپ از شاخه db-storage
        data_resp = _github_api_request(f"/contents/{BACKUP_FILE_PATH}?ref={BACKUP_BRANCH}")
        if not data_resp or "content" not in data_resp:
            return
            
        content_bytes = base64.b64decode(data_resp["content"])
        dump = json.loads(content_bytes.decode("utf-8"))
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("PRAGMA foreign_keys = OFF;")
            
            for u in dump.get("users", []):
                await db.execute("""
                    INSERT OR REPLACE INTO users (id, username, full_name, card_number, bank_name, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (u["id"], u.get("username"), u["full_name"], u.get("card_number"), u.get("bank_name"), u.get("created_at")))
                
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
                
            await db.execute("PRAGMA foreign_keys = ON;")
            await db.commit()
            print("✅ داده‌های دیتابیس با موفقیت از شاخه db-storage بازیابی شدند!")
    except Exception as e:
        print(f"Restore warning: {e}")

def schedule_cloud_backup():
    """اجرای بکاپ‌گیری در پس‌زمینه بدون معطل کردن کاربر"""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(backup_to_cloud())
    except Exception:
        pass
