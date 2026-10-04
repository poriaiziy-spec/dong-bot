import aiosqlite
import secrets
from config import DB_PATH
from random_names import get_random_member_nickname
from cloud_db_sync import restore_from_cloud, schedule_cloud_backup
from name_utils import guess_meaningful_name, is_clean_persian_name

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
            "ALTER TABLE groups ADD COLUMN tone TEXT DEFAULT 'friendly';",
            "ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1;",
            "ALTER TABLE users ADD COLUMN calling_name TEXT;"
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

        # جدول ثبت جملات ارسالی جهت عدم تکرار
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_quotes_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_index INTEGER NOT NULL,
                sent_date TEXT NOT NULL
            )
        """)

        # جدول کارت‌های بانکی اعضا (پشتیبانی از چندین شماره کارت برای هر فرد)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                card_number TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                card_title TEXT,
                is_default INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, card_number),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)

        # انتقال خودکار شماره‌کارت‌های تکی قبلی به جدول جدید
        try:
            await db.execute("""
                INSERT OR IGNORE INTO user_cards (user_id, card_number, bank_name, is_default)
                SELECT id, card_number, bank_name, 1
                FROM users
                WHERE card_number IS NOT NULL AND card_number != '';
            """)
        except Exception:
            pass

        await db.commit()
    
    # بازیابی خودکار داده‌ها در سرورهای ابری
    await restore_from_cloud()
    
    # اصلاح و یکپارچه‌سازی خودکار نام تمامی کاربران قدیمی و جدید
    await fix_all_user_names()


async def fix_all_user_names():
    """
    بررسی و اصلاح یکپارچه نام تمام کاربران (قدیمی و جدید) در دیتابیس.
    اگر نام کاربری لاتین، ناقص یا غیرفارسی باشد، به معادل فارسی معنادار تبدیل می‌شود.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT id, username, full_name, calling_name FROM users") as cursor:
                rows = await cursor.fetchall()
                
            updated = False
            for r in rows:
                uid, un, fn, cn = r[0], r[1], r[2], r[3]
                if not is_clean_persian_name(cn):
                    guessed = (
                        guess_meaningful_name(cn) or 
                        guess_meaningful_name(fn, None, un)
                    )
                    if guessed and is_clean_persian_name(guessed):
                        await db.execute("UPDATE users SET calling_name = ? WHERE id = ?", (guessed, uid))
                        await db.execute("""
                            UPDATE group_members 
                            SET nickname = ? 
                            WHERE user_id = ? AND (nickname = ? OR nickname = ? OR nickname IS NULL)
                        """, (guessed, uid, fn, cn))
                        updated = True
                        
            if updated:
                await db.commit()
                schedule_cloud_backup()
    except Exception as e:
        print(f"fix_all_user_names warning: {e}")


async def get_user_calling_name(user_id: int) -> str | None:
    """دریافت نام صدا زدن معنادار و تمیز کاربر با اصلاح خودکار نام‌های قدیمی"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT calling_name, full_name, username FROM users WHERE id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            
            cn, fn, un = row[0], row[1], row[2]
            if is_clean_persian_name(cn):
                return cn
                
            # در صورتی که نام لاتین (مثل poriA Eazi) یا خالی باشد، تلاش برای حدس فارسی
            guessed = (
                guess_meaningful_name(cn) or 
                guess_meaningful_name(fn, None, un)
            )
            if guessed and is_clean_persian_name(guessed):
                await db.execute("UPDATE users SET calling_name = ? WHERE id = ?", (guessed, user_id))
                await db.execute("""
                    UPDATE group_members 
                    SET nickname = ? 
                    WHERE user_id = ? AND (nickname = ? OR nickname = ? OR nickname IS NULL)
                """, (guessed, user_id, fn, cn))
                await db.commit()
                schedule_cloud_backup()
                return guessed
            return None


async def set_user_calling_name(user_id: int, name: str):
    """تنظیم و ذخیره نام صدا زدن کاربر و به‌روزرسانی در تمام گروه‌ها"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (id, full_name, calling_name, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET calling_name = excluded.calling_name, is_active = 1
        """, (user_id, name, name))
        await db.execute("UPDATE group_members SET nickname = ? WHERE user_id = ?", (name, user_id))
        await db.commit()
        schedule_cloud_backup()


async def upsert_user(user_id: int, username: str | None, full_name: str, calling_name: str | None = None):
    """ثبت یا به‌روزرسانی اطلاعات کاربر به همراه نام معنادار فارسی"""
    if not calling_name or not is_clean_persian_name(calling_name):
        guessed = guess_meaningful_name(full_name, None, username)
        if guessed and is_clean_persian_name(guessed):
            calling_name = guessed
        else:
            calling_name = None

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT calling_name FROM users WHERE id = ?", (user_id,)) as cursor:
            existing = await cursor.fetchone()
            
        existing_cn = existing[0] if existing else None
        final_cn = calling_name
        if existing_cn and is_clean_persian_name(existing_cn):
            final_cn = existing_cn
        elif not final_cn and existing_cn:
            guessed_old = guess_meaningful_name(existing_cn)
            if guessed_old and is_clean_persian_name(guessed_old):
                final_cn = guessed_old

        await db.execute("""
            INSERT INTO users (id, username, full_name, calling_name, is_active)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                calling_name = COALESCE(?, users.calling_name),
                is_active = 1
        """, (user_id, username, full_name, final_cn, final_cn))
        await db.commit()
        schedule_cloud_backup()


async def create_group(title: str, created_by: int) -> tuple[int, str]:
    """ساخت گروه دنگ جدید و عضویت سازنده در آن همراه با نام معنادار"""
    invite_code = secrets.token_hex(4)  # کد ۸ کاراکتری یکتا
    creator_nick = await get_user_calling_name(created_by) or "رئیس"
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO groups (invite_code, title, created_by)
            VALUES (?, ?, ?)
        """, (invite_code, title, created_by))
        group_id = cursor.lastrowid

        # افزودن خود سازنده به گروه همراه با نام معنادار
        await db.execute("""
            INSERT OR IGNORE INTO group_members (group_id, user_id, nickname)
            VALUES (?, ?, ?)
        """, (group_id, created_by, creator_nick))

        await db.commit()
        schedule_cloud_backup()
        return group_id, invite_code


async def regenerate_invite_code(group_id: int, creator_id: int) -> str | None:
    """تولید مجدد کد دعوت برای باطل کردن لینک قبلی توسط سازنده گروه"""
    new_code = secrets.token_hex(4)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM groups WHERE id = ? AND created_by = ?", (group_id, creator_id)) as cursor:
            if not await cursor.fetchone():
                return None
        await db.execute("UPDATE groups SET invite_code = ? WHERE id = ?", (new_code, group_id))
        await db.commit()
        schedule_cloud_backup()
        return new_code


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


async def add_group_member(group_id: int, user_id: int, custom_name: str | None = None) -> tuple[bool, str]:
    """
    افزودن کاربر به گروه همراه با نام معنادار.
    خروجی: (آیا تازه عضو شده؟ , نام کاربر)
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # بررسی عضویت قبلی
        async with db.execute("SELECT nickname FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id)) as cursor:
            row = await cursor.fetchone()
            if row:
                existing_nick = row[0]
                if custom_name and custom_name != existing_nick:
                    await db.execute("UPDATE group_members SET nickname = ? WHERE group_id = ? AND user_id = ?", (custom_name, group_id, user_id))
                    await db.commit()
                    schedule_cloud_backup()
                    return False, custom_name
                return False, existing_nick

        # عضو جدید
        nickname = custom_name or await get_user_calling_name(user_id) or "همراه"
        await db.execute("""
            INSERT INTO group_members (group_id, user_id, nickname)
            VALUES (?, ?, ?)
        """, (group_id, user_id, nickname))
        await db.commit()
        schedule_cloud_backup()
        return True, nickname


async def remove_group_member(group_id: int, user_id: int) -> bool:
    """حذف یک عضو از گروه توسط سرگروه"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            DELETE FROM group_members
            WHERE group_id = ? AND user_id = ?
        """, (group_id, user_id))
        await db.commit()
        schedule_cloud_backup()
        return cursor.rowcount > 0


async def delete_group(group_id: int, creator_id: int) -> bool:
    """حذف کامل یک گروه دنگ توسط سازنده آن"""
    async with aiosqlite.connect(DB_PATH) as db:
        # بررسی اینکه آیا کاربر واقعاً سازنده گروه است
        async with db.execute("SELECT id FROM groups WHERE id = ? AND created_by = ?", (group_id, creator_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False

        await db.execute("PRAGMA foreign_keys = ON;")
        cursor = await db.execute("DELETE FROM groups WHERE id = ? AND created_by = ?", (group_id, creator_id))
        await db.commit()
        schedule_cloud_backup()
        return cursor.rowcount > 0


async def get_all_user_ids() -> list[int]:
    """دریافت شناسه‌های تمام کاربران ربات جهت ارسال پیام صبحگاهی"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id FROM users WHERE is_active != 0 OR is_active IS NULL") as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def mark_user_inactive(user_id: int):
    """غیرفعال کردن کاربری که ربات را بلاک کرده"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
        await db.commit()


async def mark_user_active(user_id: int):
    """فعال کردن مجدد کاربر هنگام استفاده از ربات"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET is_active = 1 WHERE id = ?", (user_id,))
        await db.commit()


async def get_recent_quote_indices(limit: int = 35) -> list[int]:
    """دریافت لیست شناسه‌های جملات اخیراً ارسال شده جهت عدم تکرار"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT quote_index FROM daily_quotes_log ORDER BY id DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def log_sent_quote(quote_index: int, sent_date: str):
    """ثبت لاگ ارسال جمله انگیزشی امروز"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO daily_quotes_log (quote_index, sent_date) VALUES (?, ?)", (quote_index, sent_date))
        await db.commit()
        schedule_cloud_backup()




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
    """لیست اعضای یک گروه همراه با نام، یوزرنیم، شماره کارت و نام صدا زدن معنادار"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT u.id, u.full_name, u.username, u.card_number, u.bank_name, u.calling_name, gm.nickname, gm.joined_at
            FROM group_members gm
            JOIN users u ON gm.user_id = u.id
            WHERE gm.group_id = ?
            ORDER BY gm.joined_at ASC
        """, (group_id,)) as cursor:
            rows = await cursor.fetchall()
            members = []
            for r in rows:
                item = dict(r)
                name = item.get("calling_name") or item.get("nickname")
                if not name or not is_clean_persian_name(name):
                    guessed = guess_meaningful_name(item["full_name"], None, item.get("username"))
                    if guessed and is_clean_persian_name(guessed):
                        name = guessed
                    else:
                        name = item.get("nickname") or item["full_name"]
                item["nickname"] = name
                item["display_name"] = name
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
        schedule_cloud_backup()
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
        schedule_cloud_backup()
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
        schedule_cloud_backup()
        return cursor.rowcount


async def ensure_user_exists(user_id: int, full_name: str = "کاربر", username: str | None = None):
    """اطمینان از وجود داشتن رکورد کاربر در جدول users برای جلوگیری از خطای عدم ذخیره‌سازی یا کلید خارجی"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (id, username, full_name, is_active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(id) DO UPDATE SET is_active = 1
        """, (user_id, username, full_name))
        await db.commit()


async def add_user_card(user_id: int, card_number: str, bank_name: str, card_title: str | None = None) -> tuple[int, bool]:
    """
    افزودن کارت بانکی جدید برای کاربر.
    اگر اولین کارت کاربر باشد، به صورت خودکار به عنوان پیش‌فرض تنظیم می‌شود.
    خروجی: (card_id, is_new)
    """
    await ensure_user_exists(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (user_id,)) as cursor:
            count = (await cursor.fetchone())[0]
            
        is_default = 1 if count == 0 else 0
        
        try:
            cursor_ins = await db.execute("""
                INSERT INTO user_cards (user_id, card_number, bank_name, card_title, is_default)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, card_number, bank_name, card_title, is_default))
            card_id = cursor_ins.lastrowid
            
            # اگر کارت پیش‌فرض بود، اطلاعات در جدول users هم ثبت شود
            if is_default:
                await db.execute("UPDATE users SET card_number = ?, bank_name = ? WHERE id = ?", (card_number, bank_name, user_id))
                
            await db.commit()
            schedule_cloud_backup()
            return card_id, True
        except aiosqlite.IntegrityError:
            # کارت قبلاً برای این کاربر ثبت شده
            async with db.execute("SELECT id FROM user_cards WHERE user_id = ? AND card_number = ?", (user_id, card_number)) as cursor_sel:
                row = await cursor_sel.fetchone()
                return (row[0], False) if row else (0, False)


async def get_user_cards(user_id: int) -> list[dict]:
    """دریافت تمام کارت‌های بانکی ثبت‌شده کاربر (کارت پیش‌فرض در ابتدا)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM user_cards 
            WHERE user_id = ? 
            ORDER BY is_default DESC, id DESC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def get_user_card_by_id(user_id: int, card_id: int) -> dict | None:
    """دریافت مشخصات یک کارت با شناسه"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM user_cards WHERE id = ? AND user_id = ?", (card_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def set_default_card(user_id: int, card_id: int) -> bool:
    """انتخاب یک کارت به عنوان کارت اصلی و پیش‌فرض جهت نمایش در تسویه‌حساب‌ها"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT card_number, bank_name FROM user_cards WHERE id = ? AND user_id = ?", (card_id, user_id)) as cursor:
            card = await cursor.fetchone()
            if not card:
                return False
            card_num, bank = card[0], card[1]

        await db.execute("UPDATE user_cards SET is_default = 0 WHERE user_id = ?", (user_id,))
        await db.execute("UPDATE user_cards SET is_default = 1 WHERE id = ? AND user_id = ?", (card_id, user_id))
        await db.execute("UPDATE users SET card_number = ?, bank_name = ? WHERE id = ?", (card_num, bank, user_id))
        await db.commit()
        schedule_cloud_backup()
        return True


async def delete_user_card(user_id: int, card_id: int) -> bool:
    """حذف یک کارت بانکی"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT is_default FROM user_cards WHERE id = ? AND user_id = ?", (card_id, user_id)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return False
            was_default = row[0]

        await db.execute("DELETE FROM user_cards WHERE id = ? AND user_id = ?", (card_id, user_id))
        
        # اگر کارت پیش‌فرض حذف شد، کارت دیگری را پیش‌فرض کن
        if was_default:
            async with db.execute("SELECT id, card_number, bank_name FROM user_cards WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)) as cursor_next:
                next_card = await cursor_next.fetchone()
                if next_card:
                    await db.execute("UPDATE user_cards SET is_default = 1 WHERE id = ?", (next_card[0],))
                    await db.execute("UPDATE users SET card_number = ?, bank_name = ? WHERE id = ?", (next_card[1], next_card[2], user_id))
                else:
                    await db.execute("UPDATE users SET card_number = NULL, bank_name = NULL WHERE id = ?", (user_id,))

        await db.commit()
        schedule_cloud_backup()
        return True


async def get_user_card(user_id: int) -> dict:
    """دریافت کارت اصلی کاربر (سازگاری با کدهای موجود)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT card_number, bank_name FROM user_cards WHERE user_id = ? ORDER BY is_default DESC, id DESC LIMIT 1", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
        async with db.execute("SELECT card_number, bank_name FROM users WHERE id = ?", (user_id,)) as cursor_u:
            row_u = await cursor_u.fetchone()
            if row_u and row_u["card_number"]:
                return dict(row_u)
            return {"card_number": None, "bank_name": None}


async def update_user_card(user_id: int, card_number: str | None, bank_name: str | None):
    """ذخیره یا ویرایش شماره کارت (جهت سازگاری با سایر بخش‌ها)"""
    if card_number and bank_name:
        await add_user_card(user_id, card_number, bank_name)
    else:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET card_number = NULL, bank_name = NULL WHERE id = ?", (user_id,))
            await db.execute("DELETE FROM user_cards WHERE user_id = ?", (user_id,))
            await db.commit()
            schedule_cloud_backup()


async def set_group_tone(group_id: int, tone: str):
    """تنظیم لحن مکالمه گروه (formal, friendly, toxic)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE groups SET tone = ? WHERE id = ?", (tone, group_id))
        await db.commit()
        schedule_cloud_backup()


async def get_group_tone(group_id: int) -> str:
    """دریافت لحن مکالمه گروه (پیش‌فرض: friendly)"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT tone FROM groups WHERE id = ?", (group_id,)) as cursor:
            row = await cursor.fetchone()
            if row and row["tone"]:
                return row["tone"]
            return "friendly"


async def reset_all_database():
    """پاکسازی کامل و ریست تمام اطلاعات دیتابیس (جداول، گروه‌ها، اعضا و هزینه‌ها)"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = OFF;")
        await db.execute("DELETE FROM expense_shares;")
        await db.execute("DELETE FROM expenses;")
        await db.execute("DELETE FROM group_members;")
        await db.execute("DELETE FROM groups;")
        await db.execute("DELETE FROM user_cards;")
        await db.execute("DELETE FROM users;")
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.commit()
        schedule_cloud_backup()


