from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import ExpenseCreationStates, ExpenseEditStates
from helpers import clean_amount_input, format_amount, safe, parse_amount_or_quantity_expression, parse_quantity, format_quantity
from tones import (
    msg_expense_title_prompt,
    msg_expense_amount_prompt,
    msg_expense_payer_prompt,
    msg_expense_shares_prompt,
    msg_expense_saved
)

router = Router()

@router.callback_query(F.data.startswith("exp:add:"))
async def handle_start_add_expense(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    
    members = await db.get_group_members(group_id)
    if not members:
        await callback.answer("گروه عضوی ندارد!", show_alert=True)
        return
        
    tone = await db.get_group_tone(group_id)
    await state.clear()
    await state.update_data(group_id=group_id, tone=tone)
    await state.set_state(ExpenseCreationStates.waiting_for_title)
    
    text = msg_expense_title_prompt(tone)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.cancel_keyboard(group_id))


@router.message(ExpenseCreationStates.waiting_for_title)
async def handle_expense_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    calling_name = await db.get_user_calling_name(message.from_user.id) or "جان دلم"
    if len(title) < 2 or len(title) > 80:
        await message.answer(f"⚠️ {safe(calling_name)} جانم، لطفاً عنوانی بین ۲ تا ۸۰ حرف برام بنویس:")
        return

    await state.update_data(title=title)
    await state.set_state(ExpenseCreationStates.waiting_for_amount)
    
    data = await state.get_data()
    group_id = data.get("group_id")
    tone = data.get("tone") or (await db.get_group_tone(group_id) if group_id else "friendly")
    
    await db.cleanup_chat_history(message.bot, message.from_user.id)
    text = msg_expense_amount_prompt(tone, title)
    sent = await message.answer(text, parse_mode="HTML", reply_markup=kb.expense_amount_choice_keyboard(group_id))
    await db.record_chat_message(message.from_user.id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("exp:mode_qty:"))
async def handle_start_unit_price_mode(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    title = data.get("title", "هزینه")
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"

    await state.set_state(ExpenseCreationStates.waiting_for_unit_price)

    text = (
        f"🏷️ شرح هزینه: <b>«{safe(title)}»</b>\n\n"
        f"💵 <b>قیمت واحد (فی هر یک عدد)</b> چقدره {safe(calling_name)} قشنگم؟\n"
        "لطفاً مبلغ رو به <b>تومان</b> برام بفرست:\n"
        "<i>(مثلاً: <code>35000</code> یا <code>۳۵ هزار</code> یا <code>35k</code>)</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"grp:sec_exp:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.message(ExpenseCreationStates.waiting_for_unit_price)
async def handle_expense_unit_price(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")
    title = data.get("title", "هزینه")

    unit_price = clean_amount_input(message.text)
    if not unit_price or unit_price <= 0:
        sent = await message.answer(
            f"⚠️ مبلغ قیمت واحد نامعتبر است {safe(calling_name)} جانم! لطفاً عددی به تومان بفرست (مثلاً: <code>35000</code> یا <code>۳۵ هزار</code>):",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ انصراف", callback_data=f"grp:sec_exp:{group_id}")]
            ])
        )
        await db.record_chat_message(user_id, sent.message_id)
        try:
            await message.delete()
        except Exception:
            pass
        return

    await state.update_data(unit_price=unit_price)
    await state.set_state(ExpenseCreationStates.waiting_for_quantity)
    await db.cleanup_chat_history(message.bot, user_id)

    prompt_text = (
        f"🏷️ شرح هزینه: <b>«{safe(title)}»</b>\n"
        f"💵 قیمت واحد: <b>{format_amount(unit_price)}</b>\n\n"
        f"🔢 <b>تعداد یا مقدارش</b> چنده {safe(calling_name)} قشنگم؟\n"
        "<i>(مثلاً: <code>4</code> یا <code>۲</code> یا حتی اعشاری مثل <code>1.5</code>)</i>"
    )
    sent = await message.answer(
        prompt_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ انصراف", callback_data=f"grp:sec_exp:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.message(ExpenseCreationStates.waiting_for_quantity)
async def handle_expense_quantity(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")
    title = data.get("title", "هزینه")
    unit_price = data.get("unit_price", 0)
    tone = data.get("tone") or (await db.get_group_tone(group_id) if group_id else "friendly")

    qty = parse_quantity(message.text)
    if not qty or qty <= 0:
        sent = await message.answer(
            f"⚠️ مقدار یا تعداد نامعتبر است {safe(calling_name)} قشنگم! لطفاً عددی مانند <code>4</code> یا <code>1.5</code> بفرست:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ انصراف", callback_data=f"grp:sec_exp:{group_id}")]
            ])
        )
        await db.record_chat_message(user_id, sent.message_id)
        try:
            await message.delete()
        except Exception:
            pass
        return

    total_amount = int(round(unit_price * qty))
    calc_desc = f"{format_amount(unit_price)} × {format_quantity(qty)}"
    await state.update_data(amount=total_amount)
    await state.set_state(ExpenseCreationStates.waiting_for_payer)

    members = await db.get_group_members(group_id)
    await db.cleanup_chat_history(message.bot, user_id)

    prompt = msg_expense_payer_prompt(tone, title, f"{format_amount(total_amount)} ({calc_desc})")
    sent = await message.answer(
        prompt,
        parse_mode="HTML",
        reply_markup=kb.payer_select_keyboard(group_id, members, user_id)
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.message(ExpenseCreationStates.waiting_for_amount)
async def handle_expense_amount(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "عزیز دلم"
    data = await state.get_data()
    group_id = data.get("group_id")
    title = data.get("title", "هزینه")
    tone = data.get("tone") or (await db.get_group_tone(group_id) if group_id else "friendly")

    amount, calc_detail = parse_amount_or_quantity_expression(message.text)
    if not amount or amount <= 0:
        sent = await message.answer(
            f"⚠️ مبلغ یا فرمول نامعتبره {safe(calling_name)} قشنگم! لطفاً مبلغ کل (مثلاً: <code>250000</code>) یا ضرب قیمت واحد در تعداد (مثلاً: <code>35000 * 4</code> یا <code>۴ تا ۳۵ هزار</code>) رو برام بفرست:",
            parse_mode="HTML",
            reply_markup=kb.expense_amount_choice_keyboard(group_id)
        )
        await db.record_chat_message(user_id, sent.message_id)
        try:
            await message.delete()
        except Exception:
            pass
        return

    calc_desc = ""
    if calc_detail:
        calc_desc = f" ({format_amount(calc_detail['unit_price'])} × {format_quantity(calc_detail['quantity'])})"

    await state.update_data(amount=amount)
    members = await db.get_group_members(group_id)
    await state.set_state(ExpenseCreationStates.waiting_for_payer)

    await db.cleanup_chat_history(message.bot, user_id)
    text = msg_expense_payer_prompt(tone, title, f"{format_amount(amount)}{calc_desc}")
    sent = await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb.payer_select_keyboard(group_id, members, user_id)
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("fsm:payer:"))
async def handle_payer_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    payer_id = int(callback.data.split(":")[2])
    
    data = await state.get_data()
    group_id = data.get("group_id")
    if not group_id:
        await callback.message.edit_text("جلسه منقضی شده است.", reply_markup=kb.main_menu_keyboard())
        return
        
    await state.update_data(payer_id=payer_id)
    
    members = await db.get_group_members(group_id)
    # به صورت پیش‌فرض همه اعضا انتخاب می‌شوند
    all_member_ids = {m["id"] for m in members}
    await state.update_data(selected_shares=list(all_member_ids))
    await state.set_state(ExpenseCreationStates.waiting_for_shares)
    
    payer_user = next((m for m in members if m["id"] == payer_id), None)
    payer_name = (payer_user.get("display_name") or payer_user.get("nickname") or payer_user["full_name"]) if payer_user else "نامشخص"
    tone = data.get("tone") or (await db.get_group_tone(group_id) if group_id else "friendly")
    
    text = msg_expense_shares_prompt(tone, data["title"], format_amount(data["amount"]), payer_name)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.shares_select_keyboard(group_id, members, all_member_ids)
    )


@router.callback_query(F.data.startswith("fsm:share:toggle:"))
async def handle_share_toggle(callback: CallbackQuery, state: FSMContext):
    toggle_id = int(callback.data.split(":")[3])
    data = await state.get_data()
    group_id = data["group_id"]
    
    selected_set = set(data.get("selected_shares", []))
    if toggle_id in selected_set:
        if len(selected_set) == 1:
            await callback.answer("حداقل یک نفر باید سهیم باشد!", show_alert=True)
            return
        selected_set.remove(toggle_id)
    else:
        selected_set.add(toggle_id)
        
    await state.update_data(selected_shares=list(selected_set))
    members = await db.get_group_members(group_id)
    
    await callback.message.edit_reply_markup(
        reply_markup=kb.shares_select_keyboard(group_id, members, selected_set)
    )
    await callback.answer()


@router.callback_query(F.data == "fsm:share:all")
async def handle_share_all_quick(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    group_id = data["group_id"]
    members = await db.get_group_members(group_id)
    all_member_ids = [m["id"] for m in members]
    await state.update_data(selected_shares=all_member_ids)
    await save_expense_final(callback, state)


@router.callback_query(F.data == "fsm:share:done")
async def handle_share_done(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await save_expense_final(callback, state)


async def save_expense_final(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    group_id = data.get("group_id")
    payer_id = data.get("payer_id")
    title = data.get("title")
    amount = data.get("amount")
    selected_ids = data.get("selected_shares", [])
    tone = data.get("tone") or (await db.get_group_tone(group_id) if group_id else "friendly")
    
    if not (group_id and payer_id and title and amount):
        await callback.answer("اطلاعات ثبت هزینه منقضی شده است!", show_alert=True)
        await state.clear()
        if group_id:
            await callback.message.edit_text("جلسه ثبت هزینه منقضی شده است.", reply_markup=kb.group_dashboard_keyboard(group_id))
        else:
            await callback.message.edit_text("جلسه ثبت هزینه منقضی شده است.", reply_markup=kb.main_menu_keyboard())
        return

    if not selected_ids:
        await callback.answer("حداقل یک نفر باید در دنگ سهیم باشد!", show_alert=True)
        return
        
    # محاسبه سهم هر نفر
    count = len(selected_ids)
    base_share = amount // count
    remainder = amount % count
    
    shares_dict = {}
    for i, uid in enumerate(selected_ids):
        # اضافه کردن باقیمانده به نفر اول برای تطابق دقیق با مبلغ کل
        shares_dict[uid] = base_share + (remainder if i == 0 else 0)
        
    await db.add_expense(group_id, payer_id, title, amount, shares_dict)
    if data.get("from_shopping_list"):
        await db.clear_group_shopping_items(group_id)
    await state.clear()
    
    members = await db.get_group_members(group_id)
    payer = next((m for m in members if m["id"] == payer_id), None)
    payer_name = (payer.get("display_name") or payer.get("nickname") or payer["full_name"]) if payer else "نامشخص"
    
    involved_members = [m.get("display_name") or m.get("nickname") or m["full_name"] for m in members if m["id"] in selected_ids]
    involved_text = "، ".join(involved_members)
    
    text = msg_expense_saved(
        tone=tone,
        title=title,
        amt_str=format_amount(amount),
        payer_name=payer_name,
        count=count,
        base_share_str=format_amount(base_share),
        involved_text=involved_text
    )
    
    group = await db.get_group_by_id(group_id)
    is_creator = bool(group and group["created_by"] == callback.from_user.id)
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.group_dashboard_keyboard(group_id, is_creator=is_creator)
    )


@router.callback_query(F.data.startswith("grp:history:"))
async def handle_expense_history(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    
    history = await db.get_group_history(group_id, limit=15)
    group = await db.get_group_by_id(group_id)
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    
    if not history:
        text = f"📜 هنوز هیچ هزینه‌ای برای دورهمی <b>«{safe(group['title'])}»</b> ثبت نشده {safe(calling_name)} قشنگم! ☕❤️\n\nهر وقت خریدی انجام شد، با دکمه ثبت هزینه اضافه‌ش کن تا با عشق برات حساب کنم."
        markup = kb.InlineKeyboardMarkup(inline_keyboard=[
            [kb.InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    else:
        text = (
            f"📜 <b>تاریخچه هزینه‌های دورهمی «{safe(group['title'])}»، {safe(calling_name)} جانم:</b> ☕❤️\n\n"
            "برای دیدن جزئیات یا حذف هر هزینه، روی اون بزن عزیز دلم:\n"
            "(علامت ✅: تسویه شده / علامت ⏳: فعال در این دوره)"
        )
        markup = kb.expense_history_keyboard(history, group_id)
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("exp:view:"))
async def handle_view_single_expense(callback: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    await callback.answer()
    parts = callback.data.split(":")
    exp_id = int(parts[2])
    group_id = int(parts[3])
    
    active_expenses = await db.get_active_expenses(group_id)
    expense = next((e for e in active_expenses if e["id"] == exp_id), None)
    
    if not expense:
        # جستجو در کل هزینه‌ها
        all_hist = await db.get_group_history(group_id, limit=100)
        expense = next((e for e in all_hist if e["id"] == exp_id), None)
        
    if not expense:
        await callback.answer("هزینه یافت نشد عزیز دلم!", show_alert=True)
        return

    group = await db.get_group_by_id(group_id)
    is_settled = bool(expense.get("settled"))
    can_edit = bool(group and (group["created_by"] == callback.from_user.id or expense.get("payer_id") == callback.from_user.id) and not is_settled)

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    status = "تسویه شده ✅" if is_settled else "فعال در دوره جاری ⏳"
    text = (
        f"🔍 <b>جزئیات این هزینه برای شما، {safe(calling_name)} جانم:</b> ☕❤️\n\n"
        f"🏷️ بابت: <b>{safe(expense['title'])}</b>\n"
        f"💰 مبلغ: <b>{format_amount(expense['amount'])}</b>\n"
        f"👤 پرداخت‌کننده: <b>{expense.get('payer_name', 'نامشخص')}</b>\n"
        f"📅 تاریخ: {expense.get('created_at', '')}\n"
        f"📊 وضعیت: <b>{status}</b>\n"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.single_expense_keyboard(exp_id, group_id, can_edit=can_edit)
    )


@router.callback_query(F.data.startswith("exp:edit_amt:"))
async def handle_start_edit_expense_amount(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    exp_id = int(parts[2])
    group_id = int(parts[3])
    
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return
        
    expense = await db.get_expense_by_id(exp_id, group_id)
    if not expense:
        await callback.answer("هزینه یافت نشد عزیز دلم!", show_alert=True)
        return
        
    if expense.get("settled"):
        await callback.answer("⚠️ این هزینه قبلاً تسویه شده و قابل ویرایش نیست عزیز دلم!", show_alert=True)
        return
        
    is_authorized = (
        callback.from_user.id == group["created_by"] or 
        expense.get("payer_id") == callback.from_user.id
    )
    if not is_authorized:
        await callback.answer("⚠️ فقط ثبت‌کننده این هزینه یا سرگروه مجاز به ویرایش مبلغ هستند جان دلم!", show_alert=True)
        return

    await state.clear()
    await state.set_state(ExpenseEditStates.waiting_for_new_amount)
    await state.update_data(edit_expense_id=exp_id, edit_group_id=group_id)
    
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    text = (
        f"✏️ <b>ویرایش مبلغ هزینه «{safe(expense['title'])}»</b> 🌸\n\n"
        f"💰 مبلغ فعلی: <b>{format_amount(expense['amount'])}</b>\n\n"
        f"{safe(calling_name)} قشنگم، لطفاً مبلغ جدید رو به <b>تومان</b> برام بفرست:\n"
        f"<i>(مثلاً: <code>50000</code> یا <code>۵۰ هزار</code> یا <code>50k</code>)</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"exp:view:{exp_id}:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    await callback.answer()


@router.message(ExpenseEditStates.waiting_for_new_amount)
async def handle_expense_new_amount_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    chat_id = message.chat.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    
    data = await state.get_data()
    exp_id = data.get("edit_expense_id")
    group_id = data.get("edit_group_id")
    
    if not exp_id or not group_id:
        await state.clear()
        sent = await message.answer("⚠️ اطلاعات هزینه منقضی شده است عزیز دلم.", reply_markup=kb.main_menu_keyboard())
        await db.record_chat_message(chat_id, sent.message_id)
        return
        
    amount, _ = parse_amount_or_quantity_expression(message.text or "")
    if not amount or amount <= 0:
        sent = await message.answer(
            f"⚠️ مبلغ یا فرمول نامعتبره {safe(calling_name)} قشنگم! لطفاً مبلغ جدید رو به عدد (مثلاً: <code>250000</code>) یا ضرب فی در تعداد (مثلاً: <code>35000 * 4</code>) بفرست:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ انصراف", callback_data=f"exp:view:{exp_id}:{group_id}")]
            ])
        )
        await db.record_chat_message(chat_id, sent.message_id)
        try:
            await message.delete()
        except Exception:
            pass
        return
        
    success, err_msg = await db.update_expense_amount(exp_id, group_id, amount)
    await state.clear()
    
    # تمیزکاری تاریخچه چت قبلی
    await db.cleanup_chat_history(message.bot, chat_id)
    
    if not success:
        sent = await message.answer(
            f"⚠️ {safe(err_msg or 'خطایی در به‌روزرسانی هزینه رخ داد عزیز دلم!')}",
            reply_markup=kb.group_dashboard_keyboard(group_id)
        )
        await db.record_chat_message(chat_id, sent.message_id)
        try:
            await message.delete()
        except Exception:
            pass
        return
        
    expense = await db.get_expense_by_id(exp_id, group_id)
    group = await db.get_group_by_id(group_id)
    is_settled = bool(expense.get("settled")) if expense else False
    can_edit = bool(group and (group["created_by"] == user_id or (expense and expense.get("payer_id") == user_id)) and not is_settled)
    
    status = "تسویه شده ✅" if is_settled else "فعال در دوره جاری ⏳"
    payer_name = expense.get('payer_name', 'نامشخص') if expense else 'نامشخص'
    title = expense.get('title', '') if expense else ''
    
    text = (
        f"✅ <b>مبلغ هزینه با موفقیت به‌روزرسانی و دنگ‌ها مجدداً محاسبه شدند {safe(calling_name)} جانم!</b> 🌸❤️\n\n"
        f"🏷️ بابت: <b>{safe(title)}</b>\n"
        f"💰 مبلغ جدید: <b>{format_amount(amount)}</b>\n"
        f"👤 پرداخت‌کننده: <b>{safe(payer_name)}</b>\n"
        f"📊 وضعیت: <b>{status}</b>\n"
    )
    sent = await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb.single_expense_keyboard(exp_id, group_id, can_edit=can_edit)
    )
    await db.record_chat_message(chat_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("exp:del:"))
async def handle_delete_expense(callback: CallbackQuery):
    parts = callback.data.split(":")
    exp_id = int(parts[2])
    group_id = int(parts[3])
    
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    all_expenses = await db.get_group_history(group_id, limit=200)
    target_exp = next((e for e in all_expenses if e["id"] == exp_id), None)
    
    # فقط ثبت‌کننده هزینه یا سازنده گروه مجاز به حذف هستند
    is_authorized = (
        callback.from_user.id == group["created_by"] or 
        (target_exp and target_exp.get("payer_id") == callback.from_user.id)
    )
    if not is_authorized:
        await callback.answer("⚠️ فقط ثبت‌کننده این هزینه یا سرگروه مجاز به حذف آن است عزیز دلم!", show_alert=True)
        return
    
    success = await db.delete_expense(exp_id, group_id)
    if success:
        await callback.answer("✅ هزینه با موفقیت حذف شد جان دلم.", show_alert=True)
    else:
        await callback.answer("⚠️ خطا در حذف هزینه عزیز دلم!", show_alert=True)
        
    # بازگشت به تاریخچه
    history = await db.get_group_history(group_id, limit=15)
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    if not history:
        text = f"📜 هنوز هیچ هزینه‌ای برای دورهمی <b>«{safe(group['title'])}»</b> ثبت نشده {safe(calling_name)} قشنگم."
        markup = kb.InlineKeyboardMarkup(inline_keyboard=[
            [kb.InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    else:
        text = f"📜 <b>تاریخچه هزینه‌های دورهمی «{safe(group['title'])}»، {safe(calling_name)} جانم:</b>"
        markup = kb.expense_history_keyboard(history, group_id)
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
