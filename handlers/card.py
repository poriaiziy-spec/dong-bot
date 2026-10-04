from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import CardRegistrationStates
from bank_utils import clean_card_input, format_card_number, detect_bank_name
from helpers import safe

router = Router()

@router.callback_query(F.data == "nav:my_card")
async def handle_my_card(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    
    user_id = callback.from_user.id
    # اطمینان از وجود کاربر در دیتابیس
    await db.ensure_user_exists(user_id, callback.from_user.full_name, callback.from_user.username)
    
    cards = await db.get_user_cards(user_id)
    
    if cards:
        lines = [
            f"💳 <b>کارت‌های بانکی ثبت‌شده شما ({len(cards)} کارت):</b>\n",
            "⭐ <i>کارت اصلی شما در زمان تسویه حساب به بدهکاران نمایش داده می‌شود.</i>\n"
        ]
        for idx, c in enumerate(cards, 1):
            is_def = "⭐ <b>[کارت اصلی]</b>" if c["is_default"] else ""
            formatted = format_card_number(c["card_number"])
            bank = safe(c.get("bank_name") or "بانک")
            lines.append(f"{idx}️⃣ <b>{bank}</b> {is_def}\n   🔢 <code>{formatted}</code>\n")
            
        lines.append("👇 برای مشاهده، تغییر کارت اصلی یا حذف، روی هر کارت کلیک کنید:")
        markup = kb.cards_list_keyboard(cards)
        text = "\n".join(lines)
    else:
        text = (
            "💳 <b>هنوز هیچ شماره کارتی ثبت نکرده‌اید!</b>\n\n"
            "با ثبت شماره کارت، وقتی بابت خریدهایتان از کسی طلبکار شوید، شماره کارت شما به بدهکاران نمایش داده می‌شود تا بدون معطلی واریز کنند.\n\n"
            "✨ <b>امکان جدید:</b> می‌توانید هر تعداد شماره کارت (بلو، ملی، ملت و...) که مایلید ثبت کنید و کارت اصلی را به دلخواه انتخاب کنید!"
        )
        markup = kb.card_menu_keyboard(has_card=False)
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.in_(["card:add", "card:edit"]))
async def handle_add_card_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CardRegistrationStates.waiting_for_card_number)
    
    text = (
        "💳 <b>لطفاً شماره کارت ۱۶ رقمی خود را وارد کنید:</b>\n"
        "(می‌توانید به صورت پیوسته یا با خط فاصله بفرستید، مانند: <code>6037991122334455</code>)"
    )
    cancel_markup = kb.InlineKeyboardMarkup(inline_keyboard=[
        [kb.InlineKeyboardButton(text="❌ انصراف", callback_data="nav:my_card")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=cancel_markup)


@router.message(CardRegistrationStates.waiting_for_card_number)
async def handle_card_number_input(message: Message, state: FSMContext):
    clean = clean_card_input(message.text or "")
    if not clean:
        await message.answer(
            "⚠️ شماره کارت نامعتبر است! شماره کارت باید دقیقاً ۱۶ رقم باشد. لطفاً مجدداً با دقت وارد کنید:",
            parse_mode="HTML"
        )
        return
        
    user_id = message.from_user.id
    await db.ensure_user_exists(user_id, message.from_user.full_name, message.from_user.username)
    
    detected_bank = detect_bank_name(clean)
    if detected_bank:
        card_id, is_new = await db.add_user_card(user_id, clean, detected_bank)
        await state.clear()
        
        cards = await db.get_user_cards(user_id)
        formatted = format_card_number(clean)
        if is_new:
            status_txt = "✅ <b>کارت بانکی جدید با موفقیت ثبت شد!</b>"
        else:
            status_txt = "ℹ️ این شماره کارت قبلاً در لیست شما ثبت شده بود."
            
        text = (
            f"{status_txt}\n\n"
            f"🔢 شماره کارت: <code>{formatted}</code>\n"
            f"🏦 بانک: <b>{safe(detected_bank)}</b>\n\n"
            f"💼 تعداد کل کارت‌های شما: {len(cards)} کارت"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=kb.cards_list_keyboard(cards))
    else:
        # اگر بانک به طور خودکار شناخته نشد، از کاربر نام بانک را بپرس
        await state.update_data(temp_card=clean)
        await state.set_state(CardRegistrationStates.waiting_for_bank_name)
        await message.answer(
            f"🔢 شماره کارت: <code>{format_card_number(clean)}</code>\n\n"
            "🏦 لطفاً <b>نام بانک</b> صادرکننده کارت را وارد کنید (مثلاً: بانک ملت، بلو، سامان):",
            parse_mode="HTML"
        )


@router.message(CardRegistrationStates.waiting_for_bank_name)
async def handle_bank_name_input(message: Message, state: FSMContext):
    bank_name = (message.text or "").strip()
    if len(bank_name) < 2 or len(bank_name) > 30:
        await message.answer("⚠️ لطفاً یک نام معتبر برای بانک وارد کنید:")
        return
        
    data = await state.get_data()
    card_number = data.get("temp_card")
    user_id = message.from_user.id
    await db.ensure_user_exists(user_id, message.from_user.full_name, message.from_user.username)
    
    card_id, is_new = await db.add_user_card(user_id, card_number, bank_name)
    await state.clear()
    
    cards = await db.get_user_cards(user_id)
    formatted = format_card_number(card_number)
    text = (
        "✅ <b>کارت بانکی شما با موفقیت ثبت شد!</b>\n\n"
        f"🔢 شماره کارت: <code>{formatted}</code>\n"
        f"🏦 بانک: <b>{safe(bank_name)}</b>\n\n"
        f"💼 تعداد کل کارت‌های شما: {len(cards)} کارت"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb.cards_list_keyboard(cards))


@router.callback_query(F.data.startswith("card:view:"))
async def handle_view_card_detail(callback: CallbackQuery):
    await callback.answer()
    card_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    card = await db.get_user_card_by_id(user_id, card_id)
    if not card:
        await callback.answer("کارت یافت نشد!", show_alert=True)
        return
        
    is_default = bool(card.get("is_default"))
    status_label = "⭐ <b>کارت اصلی و پیش‌فرض تسویه حساب</b>" if is_default else "▫️ کارت فرعی"
    formatted = format_card_number(card["card_number"])
    bank = safe(card.get("bank_name") or "بانک")
    
    text = (
        "💳 <b>مشخصات کارت بانکی:</b>\n\n"
        f"🏦 بانک: <b>{bank}</b>\n"
        f"🔢 شماره کارت: <code>{formatted}</code>\n"
        f"📌 وضعیت: {status_label}\n\n"
        "💡 <i>در زمان تسویه، کارت ستاره‌دار به عنوان شماره حساب شما به اعضای گروه نمایش داده می‌شود.</i>"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.card_detail_keyboard(card_id, is_default)
    )


@router.callback_query(F.data.startswith("card:set_def:"))
async def handle_set_default_card(callback: CallbackQuery):
    card_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    success = await db.set_default_card(user_id, card_id)
    if success:
        await callback.answer("⭐ این کارت به عنوان کارت اصلی تسویه انتخاب شد!", show_alert=True)
    else:
        await callback.answer("⚠️ خطا در تنظیم کارت اصلی!", show_alert=True)
        
    cards = await db.get_user_cards(user_id)
    lines = [
        f"💳 <b>کارت‌های بانکی ثبت‌شده شما ({len(cards)} کارت):</b>\n",
        "⭐ <i>کارت اصلی تغییر یافت و در تسویه‌ها نمایش داده خواهد شد.</i>\n"
    ]
    for idx, c in enumerate(cards, 1):
        is_def = "⭐ <b>[کارت اصلی]</b>" if c["is_default"] else ""
        formatted = format_card_number(c["card_number"])
        bank = safe(c.get("bank_name") or "بانک")
        lines.append(f"{idx}️⃣ <b>{bank}</b> {is_def}\n   🔢 <code>{formatted}</code>\n")
        
    markup = kb.cards_list_keyboard(cards)
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("card:del_confirm:"))
async def handle_del_card_confirm(callback: CallbackQuery):
    await callback.answer()
    card_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    card = await db.get_user_card_by_id(user_id, card_id)
    if not card:
        await callback.answer("کارت یافت نشد!", show_alert=True)
        return
        
    formatted = format_card_number(card["card_number"])
    bank = safe(card.get("bank_name") or "بانک")
    text = (
        "⚠️ <b>تأییدیه حذف کارت بانکی:</b>\n\n"
        f"آیا مطمئن هستید که می‌خواهید کارت <b>{bank}</b> (<code>{formatted}</code>) را حذف کنید؟"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.card_delete_confirm_keyboard(card_id))


@router.callback_query(F.data.startswith("card:del_do:"))
async def handle_del_card_do(callback: CallbackQuery):
    card_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id
    
    success = await db.delete_user_card(user_id, card_id)
    if success:
        await callback.answer("🗑️ کارت با موفقیت حذف شد.", show_alert=True)
    else:
        await callback.answer("⚠️ خطا در حذف کارت!", show_alert=True)
        
    # بازگشت به لیست کارت‌ها
    cards = await db.get_user_cards(user_id)
    if cards:
        lines = [
            f"💳 <b>کارت‌های بانکی ثبت‌شده شما ({len(cards)} کارت):</b>\n",
            "⭐ <i>کارت اصلی شما در زمان تسویه حساب به بدهکاران نمایش داده می‌شود.</i>\n"
        ]
        for idx, c in enumerate(cards, 1):
            is_def = "⭐ <b>[کارت اصلی]</b>" if c["is_default"] else ""
            formatted = format_card_number(c["card_number"])
            bank = safe(c.get("bank_name") or "بانک")
            lines.append(f"{idx}️⃣ <b>{bank}</b> {is_def}\n   🔢 <code>{formatted}</code>\n")
            
        markup = kb.cards_list_keyboard(cards)
        text = "\n".join(lines)
    else:
        text = (
            "💳 <b>تمام کارت‌های بانکی شما حذف شدند!</b>\n\n"
            "می‌توانید با دکمه زیر شماره کارت جدید ثبت کنید:"
        )
        markup = kb.card_menu_keyboard(has_card=False)
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "card:delete")
async def handle_delete_legacy(callback: CallbackQuery):
    user_id = callback.from_user.id
    await db.update_user_card(user_id, None, None)
    await callback.answer("🗑️ کارت‌های شما حذف شدند.", show_alert=True)
    text = (
        "💳 <b>شماره کارت‌های شما با موفقیت حذف شدند.</b>\n\n"
        "می‌توانید هر زمان خواستید کارت جدید ثبت کنید:"
    )
    await callback.message.edit_text(text, reply_markup=kb.card_menu_keyboard(has_card=False))
