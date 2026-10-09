from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import WEB_APP_URL

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """منوی اصلی ربات به همراه دکمه ورود به مینی‌اپ"""
    keyboard = [
        [
            InlineKeyboardButton(text="📱 مینی‌اپ کافه دنگ ☕✨", web_app=WebAppInfo(url=f"{WEB_APP_URL}/app"))
        ],
        [
            InlineKeyboardButton(text="➕ ایجاد گروه دنگ جدید", callback_data="nav:new_group"),
            InlineKeyboardButton(text="👥 گروه‌های من", callback_data="nav:my_groups")
        ],
        [
            InlineKeyboardButton(text="💳 شماره کارت بانکی من", callback_data="nav:my_card"),
            InlineKeyboardButton(text="👤 نام من در ربات", callback_data="name:edit")
        ],
        [
            InlineKeyboardButton(text="ℹ️ راهنمای استفاده", callback_data="nav:help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def miniapp_keyboard(group_id: int | None = None) -> InlineKeyboardMarkup:
    """کیبورد اختصاصی باز کردن مینی‌اپ"""
    url = f"{WEB_APP_URL}/app"
    if group_id:
        url += f"?group_id={group_id}"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 ورود به مینی‌اپ کافه دنگ ☕", web_app=WebAppInfo(url=url))
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="nav:main")
        ]
    ])


def groups_list_keyboard(groups: list[dict]) -> InlineKeyboardMarkup:
    """لیست گروه‌های کاربر"""
    keyboard = []
    for g in groups:
        title = g["title"]
        members_cnt = g.get("member_count", 1)
        keyboard.append([
            InlineKeyboardButton(
                text=f"📂 {title} ({members_cnt} عضو)",
                callback_data=f"grp:view:{g['id']}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="➕ ساخت گروه جدید", callback_data="nav:new_group"),
        InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def group_dashboard_keyboard(group_id: int, is_creator: bool = False) -> InlineKeyboardMarkup:
    """داشبورد اصلی گروه به صورت شبکه ۲ در ۲ دسته‌بندی شده همراه با مینی‌اپ گروه"""
    keyboard = [
        [
            InlineKeyboardButton(text="📱 باز کردن مینی‌اپ این گروه ☕", web_app=WebAppInfo(url=f"{WEB_APP_URL}/app?group_id={group_id}"))
        ],
        [
            InlineKeyboardButton(text="💰 هزینه‌ها و دنگ", callback_data=f"grp:sec_exp:{group_id}"),
            InlineKeyboardButton(text="📊 حساب‌ها و تسویه", callback_data=f"grp:sec_settle:{group_id}")
        ],
        [
            InlineKeyboardButton(text="🛒 خریدهای خونه / لیست مایحتاج", callback_data=f"shop:view:{group_id}"),
            InlineKeyboardButton(text="🍕 گردونه غذا", callback_data=f"food:start:{group_id}")
        ],
        [
            InlineKeyboardButton(text="⚙️ تنظیمات و مدیریت", callback_data=f"grp:sec_settings:{group_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت به لیست گروه‌ها", callback_data="nav:my_groups")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def group_expenses_section_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """بخش ۱: ثبت و مدیریت هزینه‌ها"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 ثبت سریع هزینه کلی", callback_data=f"exp:add:{group_id}")
        ],
        [
            InlineKeyboardButton(text="🛒 خریدهای خونه و لیست مایحتاج", callback_data=f"shop:view:{group_id}")
        ],
        [
            InlineKeyboardButton(text="📜 تاریخچه و ویرایش هزینه‌ها", callback_data=f"grp:history:{group_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت به منوی دورهمی", callback_data=f"grp:view:{group_id}")
        ]
    ])


def shopping_list_keyboard(group_id: int, has_items: bool = False) -> InlineKeyboardMarkup:
    """کیبورد صفحه اصلی لیست خرید و خریدهای خونه"""
    keyboard = [
        [
            InlineKeyboardButton(text="➕ افزودن قلم به لیست خرید", callback_data=f"shop:add:{group_id}")
        ]
    ]
    if has_items:
        keyboard.append([
            InlineKeyboardButton(text="🛍️ من خریدم (انتخاب و ثبت دنگ)", callback_data=f"shop:bmenu:{group_id}")
        ])
        keyboard.append([
            InlineKeyboardButton(text="💾 ثبت یکجای کل فاکتور", callback_data=f"shop:to_exp:{group_id}")
        ])
        keyboard.append([
            InlineKeyboardButton(text="🗑️ حذف قلم", callback_data=f"shop:del_menu:{group_id}"),
            InlineKeyboardButton(text="🧹 خالی کردن لیست", callback_data=f"shop:clear_confirm:{group_id}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 بازگشت به منوی دورهمی", callback_data=f"grp:view:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def shopping_buy_items_keyboard(items: list[dict], group_id: int, selected_ids: set[int]) -> InlineKeyboardMarkup:
    """کیبورد چندانتخابی اقلام خریداری‌شده برای تبدیل به دنگ"""
    keyboard = []
    for it in items[:15]:
        iid = it["id"]
        is_sel = iid in selected_ids
        icon = "✅" if is_sel else "⬜"
        name_short = it["item_name"][:20]
        keyboard.append([
            InlineKeyboardButton(
                text=f"{icon} {name_short}",
                callback_data=f"shop:btog:{group_id}:{iid}"
            )
        ])
    
    sel_count = len(selected_ids)
    if sel_count > 0:
        keyboard.append([
            InlineKeyboardButton(
                text=f"➡️ تایید و ثبت مبلغ ({sel_count} قلم)",
                callback_data=f"shop:bconf:{group_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="🔘 انتخاب همه", callback_data=f"shop:ball:{group_id}"),
        InlineKeyboardButton(text="🔄 پاک کردن", callback_data=f"shop:bnone:{group_id}")
    ])
    keyboard.append([
        InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data=f"shop:view:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def shopping_del_items_keyboard(items: list[dict], group_id: int) -> InlineKeyboardMarkup:
    """کیبورد انتخاب قلم جهت حذف"""
    keyboard = []
    for it in items[:15]:
        total_str = f"{it['total_price']:,} ت"
        name_short = it['item_name'][:18]
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ {name_short} ({total_str})",
                callback_data=f"shop:del_do:{it['id']}:{group_id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 بازگشت به لیست خرید", callback_data=f"shop:view:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def shopping_clear_confirm_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """تأییدیه خالی کردن تمام اقلام لیست خرید"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ بله، کل لیست پاک شود", callback_data=f"shop:clear_do:{group_id}")],
        [InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data=f"shop:view:{group_id}")]
    ])


def group_settle_section_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """بخش ۲: گزارش‌های مالی و تسویه حساب"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 وضعیت حساب‌ها و تراز", callback_data=f"grp:report:{group_id}"),
            InlineKeyboardButton(text="⚖️ فرمول تسویه حساب", callback_data=f"grp:settle_calc:{group_id}")
        ],
        [
            InlineKeyboardButton(text="🔄 صفر کردن دوره حساب‌ها", callback_data=f"grp:zero_confirm:{group_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت به منوی دورهمی", callback_data=f"grp:view:{group_id}")
        ]
    ])


def group_settings_section_keyboard(group_id: int, is_creator: bool = False) -> InlineKeyboardMarkup:
    """بخش ۳: تنظیمات و مدیریت دورهمی"""
    keyboard = [
        [
            InlineKeyboardButton(text="💌 کارت دعوت اعضا", callback_data=f"grp:invite:{group_id}"),
            InlineKeyboardButton(text="🎭 تغییر لحن ربات", callback_data=f"grp:tone_menu:{group_id}")
        ]
    ]
    if is_creator:
        keyboard.append([
            InlineKeyboardButton(text="👑 مدیریت و اخراج اعضا", callback_data=f"grp:members_manage:{group_id}"),
            InlineKeyboardButton(text="🗑️ حذف کامل گروه", callback_data=f"grp:del_confirm:{group_id}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 بازگشت به منوی دورهمی", callback_data=f"grp:view:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def group_delete_confirm_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """تأییدیه حذف کامل گروه توسط سرگروه"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ بله، گروه کلاً حذف شود", callback_data=f"grp:del_do:{group_id}")],
        [InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data=f"grp:sec_settings:{group_id}")]
    ])


def members_kick_keyboard(group_id: int, members: list[dict], creator_id: int) -> InlineKeyboardMarkup:
    """لیست اعضای قابل اخراج توسط سرگروه"""
    keyboard = []
    for m in members:
        if m["id"] == creator_id:
            continue  # سرگروه نمی‌تواند خودش را اخراج کند
        name_label = m.get("display_name", m["full_name"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"❌ اخراج {name_label}",
                callback_data=f"grp:kick_confirm:{group_id}:{m['id']}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 بازگشت به تنظیمات", callback_data=f"grp:sec_settings:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def kick_confirm_keyboard(group_id: int, member_id: int) -> InlineKeyboardMarkup:
    """تأییدیه اخراج عضو از گروه"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ بله، اخراج شود", callback_data=f"grp:kick_do:{group_id}:{member_id}")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"grp:members_manage:{group_id}")]
    ])



def tone_selection_keyboard(group_id: int, current_tone: str = "friendly") -> InlineKeyboardMarkup:
    """انتخاب لحن مکالمه ربات برای گروه"""
    tones = [
        ("formal", "👔 رسمی و اداری"),
        ("friendly", "😊 دوستانه و محاوره"),
        ("toxic", "🔞 بی‌ادب و خفن (+18)")
    ]
    buttons = []
    for t_key, t_label in tones:
        selected_mark = " ✅" if t_key == current_tone else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{t_label}{selected_mark}",
                callback_data=f"grp:set_tone:{group_id}:{t_key}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت به تنظیمات", callback_data=f"grp:sec_settings:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def cards_list_keyboard(cards: list[dict]) -> InlineKeyboardMarkup:
    """لیست کارت‌های بانکی ثبت‌شده به همراه دکمه افزودن و منو"""
    buttons = []
    for c in cards:
        is_def = "⭐ " if c.get("is_default") else "💳 "
        card_num = c.get("card_number", "")
        last4 = card_num[-4:] if len(card_num) >= 4 else ""
        bank = c.get("bank_name") or "بانک"
        def_tag = " (اصلی)" if c.get("is_default") else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{is_def}{bank} •••• {last4}{def_tag}",
                callback_data=f"card:view:{c['id']}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="➕ افزودن کارت بانکی جدید", callback_data="card:add")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def card_detail_keyboard(card_id: int, is_default: bool) -> InlineKeyboardMarkup:
    """کیبورد مدیریت یک کارت مشخص"""
    buttons = []
    if not is_default:
        buttons.append([
            InlineKeyboardButton(text="⭐ انتخاب به عنوان کارت پیش‌فرض تسویه", callback_data=f"card:set_def:{card_id}")
        ])
    buttons.append([
        InlineKeyboardButton(text="🗑️ حذف این کارت", callback_data=f"card:del_confirm:{card_id}")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت به لیست کارت‌ها", callback_data="nav:my_card")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def card_delete_confirm_keyboard(card_id: int) -> InlineKeyboardMarkup:
    """تأییدیه حذف کارت بانکی"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ بله، کارت حذف شود", callback_data=f"card:del_do:{card_id}")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"card:view:{card_id}")]
    ])


def card_menu_keyboard(has_card: bool) -> InlineKeyboardMarkup:
    """منوی ساده سازگاری برای کارت بانکی"""
    buttons = [
        [InlineKeyboardButton(text="➕ ثبت شماره کارت جدید", callback_data="card:add")]
    ]
    buttons.append([
        InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)



def group_naming_choice_keyboard() -> InlineKeyboardMarkup:
    """انتخاب نحوه نام‌گذاری گروه (رندوم خنده‌دار یا دستی)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 اسم رندوم خنده‌دار (+18)", callback_data="grp:name:random")],
        [InlineKeyboardButton(text="✍️ نوشتن اسم دلخواه خودم", callback_data="grp:name:custom")],
        [InlineKeyboardButton(text="🔙 انصراف", callback_data="nav:my_groups")]
    ])


def group_naming_confirm_keyboard() -> InlineKeyboardMarkup:
    """تأیید یا تغییر مجدد اسم رندوم پیشنهادی"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ تأیید و ساخت گروه با همین اسم", callback_data="grp:name:confirm")],
        [InlineKeyboardButton(text="🔄 یه اسم رندوم دیگه پیشنهاد بده", callback_data="grp:name:random")],
        [InlineKeyboardButton(text="✍️ خودم دستی می‌نویسم", callback_data="grp:name:custom")],
        [InlineKeyboardButton(text="🔙 انصراف", callback_data="nav:my_groups")]
    ])


def payer_select_keyboard(group_id: int, members: list[dict], current_user_id: int) -> InlineKeyboardMarkup:
    """انتخاب شخص پرداخت‌کننده (همراه با لقب خنده‌دار)"""
    keyboard = []
    for m in members:
        is_me = " (شما)" if m["id"] == current_user_id else ""
        name_label = m.get("display_name", m["full_name"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"👤 {name_label}{is_me}",
                callback_data=f"fsm:payer:{m['id']}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="❌ انصراف", callback_data=f"grp:view:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def shares_select_keyboard(
    group_id: int, 
    members: list[dict], 
    selected_ids: set[int]
) -> InlineKeyboardMarkup:
    """
    انتخاب افراد سهیم در دنگ (همراه با لقب خنده‌دار)
    """
    keyboard = [
        [
            InlineKeyboardButton(text="⚡ همه اعضا (تقسیم مساوی)", callback_data="fsm:share:all")
        ]
    ]
    
    # دکمه برای هر عضو با علامت تیک یا مربع خالی
    for m in members:
        is_checked = m["id"] in selected_ids
        icon = "✅" if is_checked else "⬜"
        name_label = m.get("display_name", m["full_name"])
        keyboard.append([
            InlineKeyboardButton(
                text=f"{icon} {name_label}",
                callback_data=f"fsm:share:toggle:{m['id']}"
            )
        ])
        
    keyboard.append([
        InlineKeyboardButton(text="💾 تأیید و ثبت هزینه", callback_data="fsm:share:done"),
        InlineKeyboardButton(text="❌ انصراف", callback_data=f"grp:view:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def zero_confirm_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """تأییدیه صفر کردن حساب‌های گروه"""
    keyboard = [
        [
            InlineKeyboardButton(text="⚠️ بله، حساب‌ها تسویه و صفر شوند", callback_data=f"grp:zero_do:{group_id}")
        ],
        [
            InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data=f"grp:sec_settle:{group_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def expense_history_keyboard(expenses: list[dict], group_id: int) -> InlineKeyboardMarkup:
    """لیست هزینه‌ها به همراه امکان حذف هزینه اشتباه"""
    keyboard = []
    for exp in expenses[:10]:
        status_icon = "✅" if exp["settled"] else "⏳"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_icon} {exp['title']} ({exp['amount']:,} ت)",
                callback_data=f"exp:view:{exp['id']}:{group_id}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 بازگشت به بخش هزینه‌ها", callback_data=f"grp:sec_exp:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def single_expense_keyboard(expense_id: int, group_id: int, can_edit: bool = False) -> InlineKeyboardMarkup:
    """مشاهده جزئیات، ویرایش مبلغ یا حذف یک هزینه"""
    keyboard = []
    if can_edit:
        keyboard.append([
            InlineKeyboardButton(text="✏️ ویرایش مبلغ هزینه", callback_data=f"exp:edit_amt:{expense_id}:{group_id}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="🗑️ حذف این هزینه", callback_data=f"exp:del:{expense_id}:{group_id}")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 بازگشت به تاریخچه", callback_data=f"grp:history:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def cancel_keyboard(group_id: int | None = None) -> InlineKeyboardMarkup:
    """دکمه انصراف ساده"""
    target = f"grp:view:{group_id}" if group_id else "nav:main"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=target)]
    ])


def expense_amount_choice_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """کیبورد مرحله ورود مبلغ هزینه با گزینه ورود مرحله‌ای قیمت واحد و تعداد"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔢 ورود مرحله‌ای (قیمت واحد + تعداد)", callback_data=f"exp:mode_qty:{group_id}")
        ],
        [
            InlineKeyboardButton(text="❌ انصراف", callback_data=f"grp:sec_exp:{group_id}")
        ]
    ])


def food_picker_keyboard(group_id: int, item_count: int) -> InlineKeyboardMarkup:
    """کیبورد گردونه انتخاب غذا در مرحله دریافت گزینه‌ها"""
    keyboard = []
    if item_count >= 2:
        keyboard.append([
            InlineKeyboardButton(text=f"🎲 قرعه‌کشی کن! ({item_count} گزینه)", callback_data=f"food:spin:{group_id}")
        ])
    if item_count >= 1:
        keyboard.append([
            InlineKeyboardButton(text="🔄 پاک کردن لیست گزینه‌ها", callback_data=f"food:clear:{group_id}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def food_result_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """کیبورد نتیجه قرعه‌کشی غذا"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 یه بار دیگه قرعه بکش", callback_data=f"food:spin:{group_id}")],
        [
            InlineKeyboardButton(text="➕ افزودن گزینه جدید", callback_data=f"food:add_more:{group_id}"),
            InlineKeyboardButton(text="🗑️ شروع مجدد (لیست جدید)", callback_data=f"food:clear:{group_id}")
        ],
        [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
    ])
