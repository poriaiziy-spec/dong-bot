from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """منوی اصلی ربات"""
    keyboard = [
        [
            InlineKeyboardButton(text="➕ ایجاد گروه دنگ جدید", callback_data="nav:new_group"),
            InlineKeyboardButton(text="👥 گروه‌های من", callback_data="nav:my_groups")
        ],
        [
            InlineKeyboardButton(text="💳 شماره کارت بانکی من", callback_data="nav:my_card"),
            InlineKeyboardButton(text="ℹ️ راهنمای استفاده", callback_data="nav:help")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


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
    """داشبورد و امکانات گروه دنگ"""
    keyboard = [
        [
            InlineKeyboardButton(text="💸 ثبت هزینه جدید", callback_data=f"exp:add:{group_id}"),
            InlineKeyboardButton(text="🍕 انتخاب رندوم غذا", callback_data=f"food:start:{group_id}")
        ],
        [
            InlineKeyboardButton(text="📊 گزارش حساب‌ها", callback_data=f"grp:report:{group_id}"),
            InlineKeyboardButton(text="⚖️ فرمول تسویه حساب", callback_data=f"grp:settle_calc:{group_id}")
        ],
        [
            InlineKeyboardButton(text="📜 تاریخچه هزینه‌ها", callback_data=f"grp:history:{group_id}"),
            InlineKeyboardButton(text="🔄 صفر کردن حساب‌ها", callback_data=f"grp:zero_confirm:{group_id}")
        ],
        [
            InlineKeyboardButton(text="🎭 تغییر لحن ربات", callback_data=f"grp:tone_menu:{group_id}"),
            InlineKeyboardButton(text="💌 کارت دعوت اعضا", callback_data=f"grp:invite:{group_id}")
        ]
    ]
    
    # دکمه‌های سرگروه
    if is_creator:
        keyboard.append([
            InlineKeyboardButton(text="👑 مدیریت اعضا", callback_data=f"grp:members_manage:{group_id}"),
            InlineKeyboardButton(text="🗑️ حذف گروه", callback_data=f"grp:del_confirm:{group_id}")
        ])
        
    keyboard.append([
        InlineKeyboardButton(text="🔙 بازگشت به لیست گروه‌ها", callback_data="nav:my_groups")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def group_delete_confirm_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """تأییدیه حذف کامل گروه توسط سرگروه"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ بله، گروه کلاً حذف شود", callback_data=f"grp:del_do:{group_id}")],
        [InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data=f"grp:view:{group_id}")]
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
        InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")
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
        InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def card_menu_keyboard(has_card: bool) -> InlineKeyboardMarkup:
    """منوی مدیریت کارت بانکی کاربر"""
    buttons = [
        [InlineKeyboardButton(text="✏️ ثبت / ویرایش شماره کارت", callback_data="card:edit")]
    ]
    if has_card:
        buttons.append([
            InlineKeyboardButton(text="🗑️ حذف شماره کارت", callback_data="card:delete")
        ])
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
            InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data=f"grp:view:{group_id}")
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
        InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def single_expense_keyboard(expense_id: int, group_id: int) -> InlineKeyboardMarkup:
    """مشاهده جزئیات یا حذف یک هزینه"""
    keyboard = [
        [
            InlineKeyboardButton(text="🗑️ حذف این هزینه", callback_data=f"exp:del:{expense_id}:{group_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت به تاریخچه", callback_data=f"grp:history:{group_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def cancel_keyboard(group_id: int | None = None) -> InlineKeyboardMarkup:
    """دکمه انصراف ساده"""
    target = f"grp:view:{group_id}" if group_id else "nav:main"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=target)]
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
