from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import CardRegistrationStates
from bank_utils import clean_card_input, format_card_number, detect_bank_name

router = Router()

@router.callback_query(F.data == "nav:my_card")
async def handle_my_card(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    
    user_id = callback.from_user.id
    card_info = await db.get_user_card(user_id)
    card_number = card_info.get("card_number")
    bank_name = card_info.get("bank_name") or "نامشخص"
    
    if card_number:
        formatted = format_card_number(card_number)
        text = (
            f"💳 <b>اطلاعات کارت بانکی شما:</b>\n\n"
            f"🔢 شماره کارت: <code>{formatted}</code>\n"
            f"🏦 نام بانک: <b>{bank_name}</b>\n\n"
            "💡 <i>وقتی دیگران به شما بدهکار شوند، این شماره کارت در فرمول تسویه حساب به آن‌ها نمایش داده می‌شود تا بتوانند به راحتی دنگ شما را واریز کنند.</i>"
        )
        markup = kb.card_menu_keyboard(has_card=True)
    else:
        text = (
            "💳 <b>هنوز شماره کارتی ثبت نکرده‌اید!</b>\n\n"
            "با ثبت شماره کارت، وقتی بابت خریدهایتان از کسی طلبکار شوید، شماره کارت شما به بدهکاران نمایش داده می‌شود تا بدون پرسیدن شماره کارت، مستقیماً پولتان را واریز کنند."
        )
        markup = kb.card_menu_keyboard(has_card=False)
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "card:edit")
async def handle_edit_card_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(CardRegistrationStates.waiting_for_card_number)
    
    text = (
        "💳 <b>لطفاً شماره کارت ۱۶ رقمی خود را وارد کنید:</b>\n"
        "(می‌توانید به صورت پیوسته یا با فاصله و خط فاصله بفرستید، مانند: <code>6037991122334455</code>)"
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
        
    detected_bank = detect_bank_name(clean)
    if detected_bank:
        await db.update_user_card(message.from_user.id, clean, detected_bank)
        await state.clear()
        
        formatted = format_card_number(clean)
        text = (
            "✅ <b>شماره کارت شما با موفقیت ثبت شد!</b>\n\n"
            f"🔢 شماره کارت: <code>{formatted}</code>\n"
            f"🏦 بانک: <b>{detected_bank}</b>"
        )
        await message.answer(text, parse_mode="HTML", reply_markup=kb.card_menu_keyboard(has_card=True))
    else:
        # اگر بانک به طور خودکار شناخته نشد، از کاربر نام بانک را بپرس
        await state.update_data(temp_card=clean)
        await state.set_state(CardRegistrationStates.waiting_for_bank_name)
        await message.answer(
            f"🔢 شماره کارت: <code>{format_card_number(clean)}</code>\n\n"
            "🏦 لطفاً <b>نام بانک</b> صادرکننده کارت را نیز وارد کنید (مثلاً: بانک ملت، بلو، سامان):",
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
    await db.update_user_card(message.from_user.id, card_number, bank_name)
    await state.clear()
    
    formatted = format_card_number(card_number)
    text = (
        "✅ <b>کارت بانکی شما با موفقیت ثبت شد!</b>\n\n"
        f"🔢 شماره کارت: <code>{formatted}</code>\n"
        f"🏦 بانک: <b>{bank_name}</b>"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb.card_menu_keyboard(has_card=True))


@router.callback_query(F.data == "card:delete")
async def handle_delete_card(callback: CallbackQuery):
    await callback.answer()
    await db.update_user_card(callback.from_user.id, None, None)
    
    text = "🗑️ شماره کارت بانکی شما با موفقیت حذف شد."
    await callback.message.edit_text(text, reply_markup=kb.card_menu_keyboard(has_card=False))
