import aiosqlite
import secrets
from config import DB_PATH
from random_names import get_random_member_nickname

async def init_db():
    """ایجاد جداول دیتابیس در صورت عدم وجود"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON;")
        
        # جدول کاربران
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # جدول گروه‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invite_code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (id)
            )
        """)

        # اعضای گروه
        await db.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                nickname TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (group_id, user_id),
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # مایگریشن برای دیتابیس‌های موجود
        for col_sql in [
            "ALTER TABLE group_members ADD COLUMN nickname TEXT;",
            "ALTER TABLE users ADD COLUMN card_number TEXT;",
            "ALTER TABLE users ADD COLUMN bank_name TEXT;",
            "ALTER TABLE groups ADD COLUMN tone TEXT DEFAULT 'friendly';"
        ]:
            try:
                await db.execute(col_sql)
            except Exception:
                pass

        # جدول هزینه‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                payer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                amount INTEGER NOT NULL,
                settled INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups (id) ON DELETE CASCADE,
                FOREIGN KEY (payer_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # جدول سهم هر فرد در هر هزینه
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expense_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                expense_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                share_amount INTEGER NOT NULL,
                FOREIGN KEY (expense_id) REFERENCES expenses (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        await db.commit()


async def upsert_user(user_id: int, username: str | None, full_name: str):
    """ثبت یا به‌روزرسانی اطلاعات کاربر"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username, full_name))
        await db.commit()


async def create_group(title: str, created_by: int) -> tuple[int, str]:
    """ساخت گروه دنگ جدید و عضویت سازنده در آن همراه با لقب رندوم"""
    invite_code = secrets.token_hex(4)  # کد ۸ کاراکتری یکتا
    creator_nick = get_random_member_nickname()
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO groups (invite_code, title, created_by)
            VALUES (?, ?, ?)
        """, (invite_code, title, created_by))
        group_id = cursor.lastrowid

        # افزودن خود سازنده به گروه همراه با لقب رندوم
        await db.execute("""
            INSERT OR IGNORE INTO group_members (group_id, user_id, nickname)
            VALUES (?, ?, ?)
        """, (group_id, created_by, creator_nick))

        await db.commit()
        return group_id, invite_code


async def get_group_by_code(invite_code: str) -> dict | None:
    """دریافت مشخصات گروه با استفاده از کد دعوت"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM groups WHERE invite_code = ?", (invite_code,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_group_by_id(group_id: int) -> dict | None:
    """دریافت مشخصات گروه با شناسه"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM groups WHERE id = ?", (group_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def add_group_member(group_id: int, user_id: int) -> tuple[bool, str]:
    """
    افزودن کاربر به گروه همراه با اختصاص لقب رندوم خنده‌دار.
    خروجی: (آیا تازه عضو شده؟ , لقب کاربر)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # بررسی عضویت قبلی
        async with db.execute("SELECT nickname FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                existing_nick = row[0]
                if not existing_nick:
                    new_nick = get_random_member_nickname()
                    await db.execute("UPDATE group_members SET nickname = ? WHERE group_id = ? AND user_id = ?", (new_nick, group_id, user_id))
                    await db.commit()
                    return False, new_nick
                return False, existing_nick

        # عضو جدید
        nickname = get_random_member_nickname()
        await db.execute("""
            INSERT INTO group_members (group_id, user_id, nickname)
            VALUES (?, ?, ?)
        """, (group_id, user_id, nickname))
        await db.commit()
        return True, nickname


async def remove_group_member(group_id: int, user_id: int) -> bool:
    """حذف یک عضو از گروه توسط سرگروه"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            DELETE FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        await db.commit()
        return cursor.rowcount > 0



async def get_user_groups(user_id: int) -> list[dict]:
    """لیست گروه‌هایی که کاربر در آن‌ها عضو است"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT g.*, 
                   (SELECT COUNT(*) FROM group_members gm2 WHERE gm2.group_id = g.id) AS member_count
            FROM groups g
            JOIN group_members gm ON g.id = gm.group_id
            WHERE gm.user_id = ?
            ORDER BY g.created_at DESC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_group_members(group_id: int) -> list[dict]:
    """لیست اعضای یک گروه همراه با نام، یوزرنیم، شماره کارت و لقب اختصاصی"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u.id, u.full_name, u.username, u.card_number, u.bank_name, gm.nickname, gm.joined_at
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = ?
            ORDER BY gm.joined_at ASC
        """, (group_id,)) as cursor:
            rows = await cursor.fetchall()
            members = []
            for r in rows:
                item = dict(r)
                nick = item.get("nickname")
                if not nick:
                    nick = get_random_member_nickname()
                    await db.execute("UPDATE group_members SET nickname = ? WHERE group_id = ? AND user_id = ?", (nick, group_id, item["id"]))
                    await db.commit()
                    item["nickname"] = nick
                item["display_name"] = f"{item['full_name']} ({nick})"
                members.append(item)
            return members


async def add_expense(group_id: int, payer_id: int, title: str, amount: int, shares: dict[int, int]) -> int:
    """
    ثبت هزینه جدید و تسهیم آن بین اعضا
    shares: {user_id: share_amount}
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO expenses (group_id, payer_id, title, amount, settled)
            VALUES (?, ?, ?, ?, 0)
        """, (group_id, payer_id, title, amount))
        expense_id = cursor.lastrowid

        for user_id, share_amt in shares.items():
            await db.execute("""
                INSERT INTO expense_shares (expense_id, user_id, share_amount)
                VALUES (?, ?, ?)
            """, (expense_id, user_id, share_amt))

        await db.commit()
        return expense_id


async def get_active_expenses(group_id: int) -> list[dict]:
    """دریافت هزینه‌های تسویه نشده یک گروه به همراه جزئیات تسهیم"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT e.*, u.full_name AS payer_name, u.username AS payer_username
            FROM expenses e
            JOIN users u ON e.payer_id = u.id
            WHERE e.group_id = ? AND e.settled = 0
            ORDER BY e.created_at DESC
        """, (group_id,)) as cursor:
            expenses = [dict(r) for r in await cursor.fetchall()]

        # دریافت سهم‌ها برای هر هزینه
        for exp in expenses:
            async with db.execute("""
                SELECT es.user_id, es.share_amount, u.full_name, u.username
                FROM expense_shares es
                JOIN users u ON es.user_id = u.id
                WHERE es.expense_id = ?
            """, (exp["id"],)) as cursor_s:
                exp["shares"] = [dict(r) for r in await cursor_s.fetchall()]

        return expenses


async def get_group_history(group_id: int, limit: int = 20) -> list[dict]:
    """دریافت تاریخچه تمام هزینه‌ها (شامل تسویه شده و فعال)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT e.*, u.full_name AS payer_name, u.username AS payer_username
            FROM expenses e
            JOIN users u ON e.payer_id = u.id
            WHERE e.group_id = ?
            ORDER BY e.created_at DESC
            LIMIT ?
        """, (group_id, limit)) as cursor:
            return [dict(r) for r in await cursor.fetchall()]


async def delete_expense(expense_id: int, group_id: int) -> bool:
    """حذف یک هزینه"""
    async with aiosqlite.connect(DB_PATH) as db:
        # حذف سهم‌ها
        await db.execute("DELETE FROM expense_shares WHERE expense_id = ?", (expense_id,))
        cursor = await db.execute("DELETE FROM expenses WHERE id = ? AND group_id = ?", (expense_id, group_id))
        await db.commit()
        return cursor.rowcount > 0


async def settle_group(group_id: int) -> int:
    """
    صفر کردن حساب‌های گروه:
    تمام هزینه‌های فعال به وضعیت settled = 1 تغییر می‌کنند.
    تعداد هزینه‌های تسویه شده بازگردانده می‌شود.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE expenses
            SET settled = 1
            WHERE group_id = ? AND settled = 0
        """, (group_id,))
        await db.commit()
        return cursor.rowcount


async def update_user_card(user_id: int, card_number: str | None, bank_name: str | None):
    """ذخیره یا ویرایش شماره کارت و نام بانک کاربر"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET card_number = ?, bank_name = ?
            WHERE id = ?
        """, (card_number, bank_name, user_id))
        await db.commit()


async def get_user_card(user_id: int) -> dict:
    """دریافت اطلاعات کارت بانکی کاربر"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT card_number, bank_name FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return {"card_number": None, "bank_name": None}


async def set_group_tone(group_id: int, tone: str):
    """تنظیم لحن مکالمه گروه (formal, friendly, toxic)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE groups SET tone = ? WHERE id = ?", (tone, group_id))
        await db.commit()


async def get_group_tone(group_id: int) -> str:
    """دریافت لحن مکالمه گروه (پیش‌فرض: friendly)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT tone FROM groups WHERE id = ?", (group_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row["tone"]:
                return row["tone"]
            return "friendly"

