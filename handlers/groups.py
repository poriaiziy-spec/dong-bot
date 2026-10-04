from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import GroupCreationStates
from helpers import format_amount

from random_names import get_random_group_name
from tones import TONE_NAMES

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
    await state.clear()
    text = (
        "🏷️ <b>انتخاب نام برای گروه دنگ جدید:</b>\n\n"
        "می‌توانید یک اسم رندوم خنده‌دار (+18) انتخاب کنید یا اسم دلخواه خودتان را بنویسید:"
    )
    markup = kb.group_naming_choice_keyboard()
    
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "grp:name:random")
async def handle_random_group_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    random_name = get_random_group_name()
    await state.update_data(suggested_title=random_name)
    
    text = (
        "🎲 <b>اسم رندوم پیشنهادی (+18):</b>\n\n"
        f"🔥 <b>«{random_name}»</b>\n\n"
        "می‌خواهید گروه با همین نام ساخته شود یا یکی دیگر پیشنهاد دهم؟"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.group_naming_confirm_keyboard())


@router.callback_query(F.data == "grp:name:confirm")
async def handle_confirm_random_name(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    title = data.get("suggested_title") or get_random_group_name()
    await finish_group_creation(callback.message, callback.from_user, title, state, bot)


@router.callback_query(F.data == "grp:name:custom")
async def handle_custom_group_name_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(GroupCreationStates.waiting_for_title)
    text = (
        "✍️ لطفاً <b>نام گروه دنگ</b> را تایپ و ارسال کنید:\n"
        "(مثلاً: سفر شمال 🌊، هم‌خونه‌ها 🏠، ناهار شرکت 🍔)"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.cancel_keyboard())


@router.message(GroupCreationStates.waiting_for_title)
async def handle_new_group_title(message: Message, state: FSMContext, bot: Bot):
    title = (message.text or "").strip()
    if len(title) < 2 or len(title) > 60:
        await message.answer("⚠️ لطفاً نامی بین ۲ تا ۶۰ کاراکتر وارد کنید:")
        return

    await finish_group_creation(message, message.from_user, title, state, bot)


async def finish_group_creation(msg_target: Message, user, title: str, state: FSMContext, bot: Bot):
    await db.upsert_user(user.id, user.username, user.full_name)
    group_id, invite_code = await db.create_group(title, user.id)
    await state.clear()

    members = await db.get_group_members(group_id)
    creator_nick = members[0].get("nickname", "رئیس") if members else "رئیس"

    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=join_{invite_code}"

    text = (
        f"✅ گروه <b>«{title}»</b> با موفقیت ساخته شد!\n"
        f"👑 لقب شما در این گروه: <b>«{creator_nick}»</b>\n\n"
        f"🔗 <b>لینک دعوت اختصاصی گروه:</b>\n"
        f"<code>{invite_link}</code>\n\n"
        "این لینک را برای دوستانتان بفرستید تا با یک کلیک و با لقب‌های خنده‌دار رندوم به گروه ملحق شوند!"
    )
    if hasattr(msg_target, "edit_text") and msg_target.from_user.is_bot:
        await msg_target.edit_text(text, parse_mode="HTML", reply_markup=kb.group_dashboard_keyboard(group_id))
    else:
        await msg_target.answer(text, parse_mode="HTML", reply_markup=kb.group_dashboard_keyboard(group_id))


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
    
    current_tone = await db.get_group_tone(group_id)
    current_tone_name = TONE_NAMES.get(current_tone, "😊 دوستانه و محاوره")
    
    members_lines = "\n".join([f"• {m['full_name']} ➡️ <b>{m.get('nickname', '')}</b>" for m in members])
    
    text = (
        f"📁 گروه: <b>{group['title']}</b>\n\n"
        f"👥 <b>اعضا و لقب‌های گروه ({len(members)} نفر):</b>\n{members_lines}\n\n"
        f"💰 کل هزینه‌های فعال این دوره: <b>{format_amount(total_active_amount)}</b>\n"
        f"🧾 تعداد فاکتورهای تسویه نشده: <b>{len(active_expenses)}</b> مورد\n"
        f"🎭 لحن ربات در این گروه: <b>{current_tone_name}</b>\n\n"
        "یکی از عملیات زیر را انتخاب کنید:"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.group_dashboard_keyboard(group_id)
    )


@router.callback_query(F.data.startswith("grp:tone_menu:"))
async def handle_tone_menu(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    current_tone = await db.get_group_tone(group_id)
    
    text = (
        "🎭 <b>انتخاب شیوه و لحن مکالمه ربات برای این گروه:</b>\n\n"
        "می‌توانید تعیین کنید ربات در این گروه با چه سبکی پیام‌ها و یادآوری‌ها را ارسال کند:\n\n"
        "• 👔 <b>رسمی و اداری:</b> مودبانه، کاملاً محترمانه و حسابداری شیک.\n"
        "• 😊 <b>دوستانه و محاوره:</b> صمیمی، رفاقتی، عامیانه و راحت.\n"
        "• 🔞 <b>بی‌ادب و خفن (+18):</b> شوخی‌های خاک‌برسری، تیکه‌انداز، فحش‌های رفاقتی و دنگ‌گیری زوری!\n\n"
        "لحن مورد نظر خود را انتخاب کنید:"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.tone_selection_keyboard(group_id, current_tone)
    )


@router.callback_query(F.data.startswith("grp:set_tone:"))
async def handle_set_tone(callback: CallbackQuery):
    parts = callback.data.split(":")
    group_id = int(parts[2])
    new_tone = parts[3]
    
    await db.set_group_tone(group_id, new_tone)
    tone_title = TONE_NAMES.get(new_tone, new_tone)
    await callback.answer(f"✅ لحن ربات به «{tone_title}» تغییر یافت!", show_alert=True)
    
    # بازگشت به منوی تغییر لحن با علامت تیک به‌روز
    text = (
        f"✅ لحن ربات با موفقیت روی <b>{tone_title}</b> تنظیم شد.\n\n"
        "از این پس تمام پیام‌ها، گزارش‌ها و یادآوری‌ها با این لحن برای اعضا ارسال خواهد شد."
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.tone_selection_keyboard(group_id, new_tone)
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

