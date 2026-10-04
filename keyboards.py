from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """منوی اصلی ربات"""
    keyboard = [
        [
            InlineKeyboardButton(text="➕ ایجاد گروه دنگ جدید", callback_data="nav:new_group"),
            InlineKeyboardButton(text="👥 گروه‌های من", callback_data="nav:my_groups")
        ],
        [
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


def group_dashboard_keyboard(group_id: int) -> InlineKeyboardMarkup:
    """داشبورد و امکانات گروه دنگ"""
    keyboard = [
        [
            InlineKeyboardButton(text="💸 ثبت هزینه جدید", callback_data=f"exp:add:{group_id}")
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
            InlineKeyboardButton(text="🔗 لینک دعوت به گروه", callback_data=f"grp:invite:{group_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت به لیست گروه‌ها", callback_data="nav:my_groups")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def payer_select_keyboard(group_id: int, members: list[dict], current_user_id: int) -> InlineKeyboardMarkup:
    """انتخاب شخص پرداخت‌کننده"""
    keyboard = []
    for m in members:
        is_me = " (شما)" if m["id"] == current_user_id else ""
        keyboard.append([
            InlineKeyboardButton(
                text=f"👤 {m['full_name']}{is_me}",
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
    انتخاب افراد سهیم در دنگ (به‌صورت چندگزینه‌ای یا همه)
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
        keyboard.append([
            InlineKeyboardButton(
                text=f"{icon} {m['full_name']}",
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
