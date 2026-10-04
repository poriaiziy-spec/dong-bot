from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import GroupCreationStates
from helpers import format_amount

router = Router()

@router.callback_query(F.data == "nav:my_groups")
@router.message(Command("groups"))
async def handle_my_groups(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    user_id = event.from_user.id
    groups = await db.get_user_groups(user_id)
    
    if not groups:
        text = "📭 شما در حال حاضر در هیچ گروهی عضو نیستید.\nبا زدن دکمه زیر می‌توانید اولین گروه دنگ خود را بسازید:"
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ ساخت گروه جدید", callback_data="nav:new_group")],
            [InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main")]
        ])
    else:
        text = "👥 <b>گروه‌های دنگ شما:</b>\nبرای مشاهده یا مدیریت، گروه مورد نظر را انتخاب کنید:"
        markup = kb.groups_list_keyboard(groups)
        
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "nav:new_group")
@router.message(Command("newgroup"))
async def handle_new_group_start(event: Message | CallbackQuery, state: FSMContext):
    await state.set_state(GroupCreationStates.waiting_for_title)
    text = (
        "🏷️ لطفاً <b>نام گروه دنگ</b> را وارد کنید:\n"
        "(مثلاً: سفر شمال 🌊، هم‌خونه‌ها 🏠، ناهار شرکت 🍔)"
    )
    markup = kb.cancel_keyboard()
    
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=markup)


@router.message(GroupCreationStates.waiting_for_title)
async def handle_new_group_title(message: Message, state: FSMContext, bot: Bot):
    title = (message.text or "").strip()
    if len(title) < 2 or len(title) > 60:
        await message.answer("⚠️ لطفاً نامی بین ۲ تا ۶۰ کاراکتر وارد کنید:")
        return

    user = message.from_user
    await db.upsert_user(user.id, user.username, user.full_name)
    group_id, invite_code = await db.create_group(title, user.id)
    await state.clear()

    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=join_{invite_code}"

    text = (
        f"✅ گروه <b>«{title}»</b> با موفقیت ساخته شد!\n\n"
        f"🔗 <b>لینک دعوت اختصاصی گروه:</b>\n"
        f"<code>{invite_link}</code>\n\n"
        "این لینک را برای همسفران یا دوستانتان بفرستید تا با زدن روی آن وارد گروه شوند."
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb.group_dashboard_keyboard(group_id)
    )


@router.callback_query(F.data.startswith("grp:view:"))
async def handle_view_group(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    
    parts = callback.data.split(":")
    group_id = int(parts[2])
    
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.message.edit_text("⚠️ این گروه یافت نشد.", reply_markup=kb.main_menu_keyboard())
        return
        
    members = await db.get_group_members(group_id)
    active_expenses = await db.get_active_expenses(group_id)
    total_active_amount = sum(e["amount"] for e in active_expenses)
    
    members_names = "، ".join([m["full_name"] for m in members])
    
    text = (
        f"📁 گروه: <b>{group['title']}</b>\n"
        f"👥 اعضا ({len(members)} نفر): {members_names}\n\n"
        f"💰 کل هزینه‌های فعال این دوره: <b>{format_amount(total_active_amount)}</b>\n"
        f"🧾 تعداد خریدهای تسویه نشده: <b>{len(active_expenses)}</b> مورد\n\n"
        "یکی از عملیات زیر را انتخاب کنید:"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.group_dashboard_keyboard(group_id)
    )


@router.callback_query(F.data.startswith("grp:invite:"))
async def handle_group_invite(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=join_{group['invite_code']}"

    text = (
        f"🔗 <b>لینک دعوت به گروه «{group['title']}»:</b>\n\n"
        f"<code>{invite_link}</code>\n\n"
        "💡 <i>کافی است این لینک را برای دوستانتان بفرستید. به محض اینکه استارت را بزنند، به عضویت گروه در می‌آیند.</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
