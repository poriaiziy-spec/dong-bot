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
    calling_name = await db.get_user_calling_name(user_id) or "جانِ دلم"
    
    if not groups:
        text = (
            f"هنوز تو هیچ دورهمی و گروهی نیستی <b>{safe(calling_name)}</b> قشنگم! ☕❤️\n\n"
            "بیا با هم اولین گروه دنگ رو بسازیم تا رفقات رو بیاری و تمام حساب‌کتاب‌ها رو برات با عشق راست‌وریس کنم:\n"
            "👇 روی دکمه زیر بزن تا با هم شروع کنیم عزیز دلم:"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ ساخت گروه جدید", callback_data="nav:new_group")],
            [InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main")]
        ])
    else:
        text = (
            f"👥 <b>دورهمی‌های شما {safe(calling_name)} جانم:</b> ☕❤️\n\n"
            "روی هر گروهی که دوست داری بزن تا با هم بریم توی داشبوردش و به حساب‌کتاب‌ها برسیم:"
        )
        markup = kb.groups_list_keyboard(groups)
        
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        await db.cleanup_chat_history(event.bot, user_id, keep_message_id=event.message.message_id)
    else:
        await db.cleanup_chat_history(event.bot, user_id)
        sent = await event.answer(text, parse_mode="HTML", reply_markup=markup)
        await db.record_chat_message(user_id, sent.message_id)
        try:
            await event.delete()
        except Exception:
            pass


@router.callback_query(F.data == "nav:new_group")
@router.message(Command("newgroup"))
async def handle_new_group_start(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    calling_name = await db.get_user_calling_name(event.from_user.id) or "عزیز دلم"
    text = (
        f"🏷️ <b>انتخاب اسم برای دورهمی جدید، {safe(calling_name)} قشنگم:</b> ☕❤️\n\n"
        "دوست داری یه اسم رندوم و خنده‌دار (+18) برات پیشنهاد بدم یا خودت یه اسم قشنگ تو ذهنت داری؟"
    )
    markup = kb.group_naming_choice_keyboard()
    
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        await db.cleanup_chat_history(event.bot, event.from_user.id, keep_message_id=event.message.message_id)
    else:
        await db.cleanup_chat_history(event.bot, event.from_user.id)
        sent = await event.answer(text, parse_mode="HTML", reply_markup=markup)
        await db.record_chat_message(event.from_user.id, sent.message_id)
        try:
            await event.delete()
        except Exception:
            pass


@router.callback_query(F.data == "grp:name:random")
async def handle_random_group_name(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    random_name = get_random_group_name()
    await state.update_data(suggested_title=random_name)
    
    text = (
        "🎲 <b>اسم پیشنهادی برای دورهمیتون:</b> 🔥\n\n"
        f"«<b>{safe(random_name)}</b>» 😈\n\n"
        "نظرت چیه جانِ دلم؟ همین رو ثبت کنم یا یکی دیگه برات رو کنم؟"
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
        "✍️ <b>اسم دورهمی قشنگت رو برام بنویس و بفرست جانِ دلم:</b> ☕❤️\n"
        "(مثلاً: سفر شمال 🌊، دورهمی کافه 🥐، ناهار رفقا 🍔)"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.cancel_keyboard())


@router.message(GroupCreationStates.waiting_for_title)
async def handle_new_group_title(message: Message, state: FSMContext, bot: Bot):
    title = (message.text or "").strip()
    if len(title) < 2 or len(title) > 60:
        await message.answer("⚠️ جانِ دلم، لطفاً یک اسم بین ۲ تا ۶۰ حرف برام بنویس:")
        return

    await db.cleanup_chat_history(bot, message.from_user.id)
    await finish_group_creation(message, message.from_user, title, state, bot)
    try:
        await message.delete()
    except Exception:
        pass


async def finish_group_creation(msg_target: Message, user, title: str, state: FSMContext, bot: Bot):
    await db.upsert_user(user.id, user.username, user.full_name)
    group_id, invite_code = await db.create_group(title, user.id)
    await state.clear()

    members = await db.get_group_members(group_id)
    creator_nick = members[0].get("nickname", "رئیس") if members else "رئیس"
    calling_name = await db.get_user_calling_name(user.id) or "قشنگم"

    bot_info = await bot.get_me()
    invite_link = f"https://t.me/{bot_info.username}?start=join_{invite_code}"

    text = (
        f"🎉 <b>مبارکت باشه {safe(calling_name)} قشنگم! دورهمی «{safe(title)}» با عشق ساخته شد</b> ☕❤️✨\n\n"
        f"👤 نام شما در این جمع: <b>«{safe(creator_nick)}»</b>\n\n"
        "💌 <b>کارت دعوت ورود اعضا:</b>\n"
        f"👉 <a href=\"{invite_link}\"><b>[ ☕ برای ورود و عضویت در گروه لمس کنید ]</b></a>\n\n"
        "💡 <i>عزیز دلم، از داخل منوی گروه، دکمه «💌 کارت دعوت اعضا» رو بزن تا برات کارت شیک آماده کنم و بفرستی برای دوستات!</i>"
    )
    if hasattr(msg_target, "edit_text") and msg_target.from_user.is_bot:
        await msg_target.edit_text(text, parse_mode="HTML", reply_markup=kb.group_dashboard_keyboard(group_id, is_creator=True))
        await db.cleanup_chat_history(bot, user.id, keep_message_id=msg_target.message_id)
    else:
        sent = await msg_target.answer(text, parse_mode="HTML", reply_markup=kb.group_dashboard_keyboard(group_id, is_creator=True))
        await db.record_chat_message(user.id, sent.message_id)


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
    
    members_lines = "\n".join([
        f"• <b>{safe(m.get('display_name') or m.get('nickname') or m['full_name'])}</b>"
        for m in members
    ])
    
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
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    if not other_members:
        text = f"👑 فقط خودت توی این جمع هستی <b>{safe(calling_name)}</b> جانم! عضو دیگه‌ای برای حذف وجود نداره ❤️"
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    else:
        text = (
            f"👑 <b>مدیریت اعضای دورهمی «{safe(group['title'])}»، {safe(calling_name)} جانم:</b> ☕❤️\n\n"
            "روی هر عضوی که مدنظرته کلیک کن تا وضعیتش رو با هم بررسی کنیم:"
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
        await callback.answer("⚠️ فقط سرگروه مجاز است عزیز دلم!", show_alert=True)
        return
        
    await callback.answer()
    members = await db.get_group_members(group_id)
    target = next((m for m in members if m["id"] == member_id), None)
    target_name = safe(target.get("display_name", target["full_name"])) if target else "این کاربر"
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    
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
        f"⚠️ <b>بررسی حذف عضو، {safe(calling_name)} جانم:</b>\n\n"
        f"کاملاً مطمئنی که می‌خوای <b>{target_name}</b> رو از جمع «{safe(group['title'])}» حذف کنی عزیز دلم؟"
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
        await callback.answer("⚠️ فقط سرگروه مجاز است عزیز دلم!", show_alert=True)
        return
        
    members = await db.get_group_members(group_id)
    target = next((m for m in members if m["id"] == member_id), None)
    
    await db.remove_group_member(group_id, member_id)
    await callback.answer("✅ عضو با موفقیت از گروه حذف شد جان دلم.", show_alert=True)
    
    # ارسال پیام اطلاع‌رسانی به کاربر اخراج‌شده در صورت امکان
    try:
        await bot.send_message(
            member_id,
            f"ℹ️ عزیز دلم، شما توسط سرگروه از دورهمی <b>«{safe(group['title'])}»</b> کنار گذاشته شدید.",
            parse_mode="HTML"
        )
    except Exception:
        pass
        
    # بازگشت به لیست مدیریت اعضا
    members_updated = await db.get_group_members(group_id)
    other_members = [m for m in members_updated if m["id"] != group["created_by"]]
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    if not other_members:
        text = f"👑 عضو دیگری برای حذف در این گروه وجود ندارد {safe(calling_name)} جانم."
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    else:
        text = f"👑 <b>مدیریت اعضای گروه «{safe(group['title'])}»، {safe(calling_name)} جانم:</b>"
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
        await callback.answer("⚠️ فقط سرگروه مجاز به حذف گروه است عزیز دلم!", show_alert=True)
        return
        
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    await callback.answer()
    text = (
        f"⚠️ <b>هشدار حذف کامل دورهمی «{safe(group['title'])}»، {safe(calling_name)} جانم:</b> ☕💔\n\n"
        "کاملاً مطمئنی که می‌خوای این گروه رو پاک کنی عزیز دلم؟\n\n"
        "• تمام سوابق، دنگ‌ها، اعضا و حساب‌کتاب‌های این جمع پاک می‌شن و دیگه قابل برگشت نیست فدات شم!"
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
        await callback.answer("⚠️ فقط سرگروه مجاز به حذف گروه است عزیز دلم!", show_alert=True)
        return
        
    success = await db.delete_group(group_id, callback.from_user.id)
    if success:
        await callback.answer(f"✅ دورهمی «{group['title']}» با موفقیت حذف شد جان دلم.", show_alert=True)
    else:
        await callback.answer("⚠️ خطا در حذف گروه!", show_alert=True)
        
    await handle_my_groups(callback, state)


@router.callback_query(F.data.startswith("grp:tone_menu:"))
async def handle_tone_menu(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    current_tone = await db.get_group_tone(group_id)
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "قشنگم"
    
    text = (
        f"🎭 <b>انتخاب لحن مکالمه برای دورهمی «{safe(group['title'] if group else '')}»، {safe(calling_name)} قشنگم:</b> ☕❤️\n\n"
        "دوست داری تو این گروه چطوری با شما و بچه‌ها حرف بزنم جانِ دلم؟\n\n"
        "• 👔 <b>رسمی و اداری:</b> کاملاً محترمانه، مودبانه و اداری.\n"
        "• 😊 <b>دوستانه و خودمونی:</b> صمیمی، رفاقتی و عامیانه.\n"
        "• 🔞 <b>بی‌ادب و خفن (+18):</b> شوخی‌های تند، تیکه‌انداز و دنگ‌گیری زوری! 😈\n\n"
        "لحن مورد نظرت رو انتخاب کن عزیز دلم:"
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
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    await callback.answer(f"✅ لحن گروه به «{tone_title}» تغییر یافت جان دلم!", show_alert=True)
    
    text = (
        f"✅ <b>لحن صحبت در این گروه با عشق روی «{tone_title}» تنظیم شد {safe(calling_name)} جانم!</b> ☕❤️\n\n"
        "از این به بعد تمام پیام‌ها و یادآوری‌های این دورهمی به همین سبک ارسال می‌شه عزیز دلم."
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
    await callback.answer("✅ کارت دعوت با عشق برات آماده و ارسال شد جان دلم! می‌تونی برای رفقات بفرستیش.", show_alert=True)


@router.callback_query(F.data.startswith("grp:invite_regen:"))
async def handle_group_invite_regen(callback: CallbackQuery, bot: Bot):
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group or group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ فقط سرگروه مجاز به تغییر لینک دعوت است عزیز دلم!", show_alert=True)
        return

    new_code = await db.regenerate_invite_code(group_id, callback.from_user.id)
    if not new_code:
        await callback.answer("خطا در ایجاد لینک جدید!", show_alert=True)
        return

    await callback.answer("✅ لینک قبلی باطل و کارت دعوت جدید با عشق صادر شد عزیز دلم!", show_alert=True)
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

