from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import GroupCreationStates
from helpers import format_amount, safe
from calculator import calculate_group_balances

from random_names import get_random_group_name
from tones import TONE_NAMES, msg_group_dashboard

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
        f"🔥 <b>«{safe(random_name)}»</b>\n\n"
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
        f"🎉 دورهمی <b>«{safe(title)}»</b> با موفقیت در <b>کافه دنگ</b> ایجاد شد!\n"
        f"👑 لقب شما در این گروه: <b>«{safe(creator_nick)}»</b>\n\n"
        "💌 <b>کارت دعوت ورود اعضا:</b>\n"
        f"👉 <a href=\"{invite_link}\"><b>[ ☕ برای ورود و عضویت در گروه لمس کنید ]</b></a>\n\n"
        "💡 <i>از داخل منوی گروه، دکمه «💌 کارت دعوت اعضا» را بزنید تا کارت شیک و آماده فوروارد برای دوستانتان تولید شود!</i>"
    )
    if hasattr(msg_target, "edit_text") and msg_target.from_user.is_bot:
        await msg_target.edit_text(text, parse_mode="HTML", reply_markup=kb.group_dashboard_keyboard(group_id, is_creator=True))
    else:
        await msg_target.answer(text, parse_mode="HTML", reply_markup=kb.group_dashboard_keyboard(group_id, is_creator=True))


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
    current_tone_name = TONE_NAMES.get(current_tone, "😊 دوستانه و خودمونی")
    
    members_lines = "\n".join([f"• {safe(m['full_name'])} ➡️ <b>{safe(m.get('nickname', ''))}</b>" for m in members])
    
    text = msg_group_dashboard(
        tone=current_tone,
        title=group["title"],
        member_count=len(members),
        member_lines=members_lines,
        total_amount=total_active_amount,
        expenses_count=len(active_expenses),
        tone_name=current_tone_name
    )
    
    is_creator = (group["created_by"] == callback.from_user.id)
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.group_dashboard_keyboard(group_id, is_creator=is_creator)
    )


@router.callback_query(F.data.startswith("grp:members_manage:"))
async def handle_members_manage(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return
        
    if group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ فقط سرگروه مجاز به مدیریت و اخراج اعضا است!", show_alert=True)
        return
        
    await callback.answer()
    members = await db.get_group_members(group_id)
    
    # آیا عضوی غیر از سرگروه وجود دارد؟
    other_members = [m for m in members if m["id"] != group["created_by"]]
    if not other_members:
        text = "👑 شما تنها عضو این گروه هستید و عضو دیگری برای اخراج وجود ندارد."
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    else:
        text = (
            f"👑 <b>مدیریت اعضای گروه «{safe(group['title'])}»:</b>\n\n"
            "روی هر عضوی که می‌خواهید از گروه حذف شود کلیک کنید:"
        )
        markup = kb.members_kick_keyboard(group_id, members, group["created_by"])
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("grp:kick_confirm:"))
async def handle_kick_confirm(callback: CallbackQuery):
    parts = callback.data.split(":")
    group_id = int(parts[2])
    member_id = int(parts[3])
    
    group = await db.get_group_by_id(group_id)
    if group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ فقط سرگروه مجاز است!", show_alert=True)
        return
        
    await callback.answer()
    members = await db.get_group_members(group_id)
    target = next((m for m in members if m["id"] == member_id), None)
    target_name = safe(target.get("display_name", target["full_name"])) if target else "این کاربر"
    
    # بررسی بدهی یا طلب تسویه‌نشده این عضو
    balance_warning = ""
    active_expenses = await db.get_active_expenses(group_id)
    if active_expenses:
        calc = calculate_group_balances(members, active_expenses)
        member_stat = next((s for s in calc["member_stats"] if s["user"]["id"] == member_id), None)
        if member_stat and member_stat["net"] != 0:
            from helpers import format_amount
            net = member_stat["net"]
            if net > 0:
                balance_warning = f"\n\n💰 <b>توجه:</b> این عضو <b>{format_amount(net)} طلبکار</b> است و هنوز حسابش تسویه نشده!"
            else:
                balance_warning = f"\n\n💰 <b>توجه:</b> این عضو <b>{format_amount(-net)} بدهکار</b> است و هنوز حسابش تسویه نشده!"
    
    text = (
        f"⚠️ <b>تأییدیه اخراج عضو:</b>\n\n"
        f"آیا مطمئن هستید که می‌خواهید <b>{target_name}</b> را از گروه اخراج کنید؟"
        f"{balance_warning}"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.kick_confirm_keyboard(group_id, member_id))


@router.callback_query(F.data.startswith("grp:kick_do:"))
async def handle_kick_do(callback: CallbackQuery, bot: Bot):
    parts = callback.data.split(":")
    group_id = int(parts[2])
    member_id = int(parts[3])
    
    group = await db.get_group_by_id(group_id)
    if group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ فقط سرگروه مجاز است!", show_alert=True)
        return
        
    members = await db.get_group_members(group_id)
    target = next((m for m in members if m["id"] == member_id), None)
    
    await db.remove_group_member(group_id, member_id)
    await callback.answer("✅ عضو با موفقیت از گروه اخراج شد.", show_alert=True)
    
    # ارسال پیام اطلاع‌رسانی به کاربر اخراج‌شده در صورت امکان
    try:
        await bot.send_message(
            member_id,
            f"ℹ️ شما توسط سرگروه از گروه <b>«{safe(group['title'])}»</b> حذف شدید.",
            parse_mode="HTML"
        )
    except Exception:
        pass
        
    # بازگشت به لیست مدیریت اعضا
    members_updated = await db.get_group_members(group_id)
    other_members = [m for m in members_updated if m["id"] != group["created_by"]]
    if not other_members:
        text = "👑 عضو دیگری برای اخراج در گروه وجود ندارد."
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    else:
        text = f"👑 <b>مدیریت اعضای گروه «{safe(group['title'])}»:</b>"
        markup = kb.members_kick_keyboard(group_id, members_updated, group["created_by"])
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("grp:del_confirm:"))
async def handle_delete_group_confirm(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return
        
    if group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ فقط سرگروه مجاز به حذف گروه است!", show_alert=True)
        return
        
    await callback.answer()
    text = (
        f"⚠️ <b>هشدار حذف کامل گروه «{safe(group['title'])}»:</b>\n\n"
        "آیا کاملاً مطمئن هستید که می‌خواهید این گروه را حذف کنید؟\n\n"
        "• تمام سوابق، اعضا، لقب‌ها، دنگ‌ها و هزینه‌های این گروه به طور کامل پاک خواهند شد و این عملیات برگشت‌پذیر نیست!"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.group_delete_confirm_keyboard(group_id))


@router.callback_query(F.data.startswith("grp:del_do:"))
async def handle_delete_group_do(callback: CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return
        
    if group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ فقط سرگروه مجاز به حذف گروه است!", show_alert=True)
        return
        
    success = await db.delete_group(group_id, callback.from_user.id)
    if success:
        await callback.answer(f"✅ گروه «{group['title']}» با موفقیت حذف شد.", show_alert=True)
    else:
        await callback.answer("⚠️ خطا در حذف گروه!", show_alert=True)
        
    await handle_my_groups(callback, state)



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
        f"💌 <b>کارت دعوت اختصاصی کافه دنگ</b> ☕\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"سلام رفقا! ✨\n"
        f"شما به جمع دورهمی <b>«{safe(group['title'])}»</b> دعوت شدید.\n\n"
        "قراره از این به بعد تمام حساب‌کتاب‌ها، خرج‌ها و دنگ‌های مشترکمون رو در کافه دنگ دقیق و بدون دردسر مدیریت کنیم!\n\n"
        "👇 <b>برای ورود به جمع، دکمه یا لینک زیر را لمس کنید:</b>\n"
        f"👉 <a href=\"{invite_link}\"><b>[ ☕ ورود و عضویت در دورهمی «{safe(group['title'])}» ]</b></a>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    is_creator = (group["created_by"] == callback.from_user.id)
    buttons = [
        [InlineKeyboardButton(text=f"☕ ورود مستقیم به «{group['title']}»", url=invite_link)],
        [InlineKeyboardButton(text="📤 دریافت کارت دعوت آماده فوروارد", callback_data=f"grp:invite_forward:{group_id}")]
    ]
    if is_creator:
        buttons.append([InlineKeyboardButton(text="🔄 باطل کردن و ساخت لینک جدید", callback_data=f"grp:invite_regen:{group_id}")])
    buttons.append([InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")])

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("grp:invite_forward:"))
async def handle_group_invite_forward(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group:
        return
        
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=join_{group['invite_code']}"
    
    card_text = (
        f"💌 <b>دعوت‌نامه ورود به دورهمی «{safe(group['title'])}»</b> ☕\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "سلام رفیق! ✨\n"
        f"به جمع دورهمی ما در <b>کافه دنگ</b> دعوت شدی.\n\n"
        "با پیوستن به این دورهمی، تمام هزینه‌ها و دنگ‌های مشترک به صورت خودکار، دقیق و عادلانه حساب و تسویه میشه.\n\n"
        "👇 <b>جهت عضویت در گروه، روی لینک یا دکمه زیر بزن:</b>\n"
        f"👉 <a href=\"{invite_link}\"><b>[ ☕ ورود به گروه «{safe(group['title'])}» ]</b></a>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "☕ <i>کافه دنگ | مدیریت هوشمند دنگ و دورهمی</i>"
    )
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"☕ پیوستن به گروه «{group['title']}»", url=invite_link)]
    ])
    
    await callback.message.answer(card_text, parse_mode="HTML", reply_markup=markup)
    await callback.answer("✅ کارت دعوت با موفقیت تولید و ارسال شد! آن را برای دوستانتان فوروارد کنید.", show_alert=True)


@router.callback_query(F.data.startswith("grp:invite_regen:"))
async def handle_group_invite_regen(callback: CallbackQuery, bot: Bot):
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group or group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ فقط سرگروه مجاز به تغییر لینک دعوت است!", show_alert=True)
        return

    new_code = await db.regenerate_invite_code(group_id, callback.from_user.id)
    if not new_code:
        await callback.answer("خطا در ایجاد لینک جدید!", show_alert=True)
        return

    await callback.answer("✅ لینک قبلی باطل و کارت دعوت جدید صادر شد!", show_alert=True)
    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=join_{new_code}"

    text = (
        f"💌 <b>کارت دعوت جدید کافه دنگ</b> ☕\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"سلام رفقا! ✨\n"
        f"شما به جمع دورهمی <b>«{safe(group['title'])}»</b> دعوت شدید.\n\n"
        "⚠️ <i>لینک قبلی باطل شد و کارت جدید جایگزین گردید.</i>\n\n"
        "👇 <b>برای ورود به جمع، دکمه یا لینک زیر را لمس کنید:</b>\n"
        f"👉 <a href=\"{invite_link}\"><b>[ ☕ ورود و عضویت در دورهمی «{safe(group['title'])}» ]</b></a>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )
    buttons = [
        [InlineKeyboardButton(text=f"☕ ورود مستقیم به «{group['title']}»", url=invite_link)],
        [InlineKeyboardButton(text="📤 دریافت کارت دعوت آماده فوروارد", callback_data=f"grp:invite_forward:{group_id}")],
        [InlineKeyboardButton(text="🔄 ساخت مجدد لینک جدید", callback_data=f"grp:invite_regen:{group_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
    ]
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

