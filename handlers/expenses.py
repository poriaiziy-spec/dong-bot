from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import ExpenseCreationStates
from helpers import clean_amount_input, format_amount

router = Router()

@router.callback_query(F.data.startswith("exp:add:"))
async def handle_start_add_expense(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    
    members = await db.get_group_members(group_id)
    if not members:
        await callback.answer("گروه عضوی ندارد!", show_alert=True)
        return
        
    await state.clear()
    await state.update_data(group_id=group_id)
    await state.set_state(ExpenseCreationStates.waiting_for_title)
    
    text = (
        "📌 <b>بابت چه چیزی هزینه شده است؟</b>\n"
        "یک عنوان کوتاه بنویسید (مثلاً: <i>شام رستوران، بنزین، ویلا، خرید سوپرمارکت</i>):"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.cancel_keyboard(group_id))


@router.message(ExpenseCreationStates.waiting_for_title)
async def handle_expense_title(message: Message, state: FSMContext):
    title = (message.text or "").strip()
    if len(title) < 2 or len(title) > 80:
        await message.answer("⚠️ لطفاً عنوانی بین ۲ تا ۸۰ کاراکتر وارد کنید:")
        return

    await state.update_data(title=title)
    await state.set_state(ExpenseCreationStates.waiting_for_amount)
    
    data = await state.get_data()
    group_id = data.get("group_id")
    
    text = (
        f"🏷️ بابت: <b>{title}</b>\n\n"
        "💵 <b>مبلغ کل چقدر شد؟ (به تومان)</b>\n"
        "می‌توانید به صورت عدد، با ویرگول یا فارسی بفرستید\n"
        "(مثلاً: <code>450000</code> یا <code>450,000</code> یا <code>۴۵۰ هزار</code>):"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb.cancel_keyboard(group_id))


@router.message(ExpenseCreationStates.waiting_for_amount)
async def handle_expense_amount(message: Message, state: FSMContext):
    amount = clean_amount_input(message.text or "")
    if not amount or amount <= 0:
        await message.answer(
            "⚠️ مبلغ نامعتبر است! لطفاً عدد را به تومان وارد کنید (مثلاً: <code>250000</code> یا <code>۲۵۰ هزار</code>):",
            parse_mode="HTML"
        )
        return

    await state.update_data(amount=amount)
    data = await state.get_data()
    group_id = data["group_id"]
    
    members = await db.get_group_members(group_id)
    await state.set_state(ExpenseCreationStates.waiting_for_payer)
    
    text = (
        f"🏷️ بابت: <b>{data['title']}</b>\n"
        f"💰 مبلغ کل: <b>{format_amount(amount)}</b>\n\n"
        "👤 <b>این هزینه را چه کسی پرداخت کرده است؟</b>\n"
        "شخص پرداخت‌کننده را انتخاب کنید:"
    )
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb.payer_select_keyboard(group_id, members, message.from_user.id)
    )


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
    payer_name = payer_user["full_name"] if payer_user else "نامشخص"
    
    text = (
        f"🏷️ بابت: <b>{data['title']}</b>\n"
        f"💰 مبلغ: <b>{format_amount(data['amount'])}</b>\n"
        f"👤 پرداخت‌کننده: <b>{payer_name}</b>\n\n"
        "👥 <b>چه کسانی در این هزینه سهیم هستند؟</b>\n"
        "به‌صورت پیش‌فرض همه اعضا انتخاب شده‌اند. می‌توانید افراد را کم/زیاد کنید یا دکمه تأیید را بزنید:"
    )
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
    group_id = data["group_id"]
    payer_id = data["payer_id"]
    title = data["title"]
    amount = data["amount"]
    selected_ids = data.get("selected_shares", [])
    
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
    await state.clear()
    
    members = await db.get_group_members(group_id)
    payer = next((m for m in members if m["id"] == payer_id), None)
    payer_name = payer["full_name"] if payer else "نامشخص"
    
    involved_members = [m["full_name"] for m in members if m["id"] in selected_ids]
    involved_text = "، ".join(involved_members)
    
    text = (
        f"✅ <b>هزینه با موفقیت ثبت شد!</b>\n\n"
        f"🏷️ بابت: <b>{title}</b>\n"
        f"💰 مبلغ کل: <b>{format_amount(amount)}</b>\n"
        f"👤 پرداخت‌کننده: <b>{payer_name}</b>\n"
        f"👥 سهیم‌ها ({count} نفر - هر نفر ~ {format_amount(base_share)}):\n"
        f"<i>{involved_text}</i>\n"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.group_dashboard_keyboard(group_id)
    )


@router.callback_query(F.data.startswith("grp:history:"))
async def handle_expense_history(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    
    history = await db.get_group_history(group_id, limit=15)
    group = await db.get_group_by_id(group_id)
    
    if not history:
        text = f"📜 هنوز هیچ هزینه‌ای برای گروه <b>«{group['title']}»</b> ثبت نشده است."
        markup = kb.InlineKeyboardMarkup(inline_keyboard=[
            [kb.InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    else:
        text = (
            f"📜 <b>تاریخچه هزینه‌های گروه «{group['title']}»:</b>\n"
            "برای مشاهده جزئیات یا حذف هر هزینه، روی آن کلیک کنید:\n"
            "(علامت ✅: تسویه شده / علامت ⏳: فعال در این دوره)"
        )
        markup = kb.expense_history_keyboard(history, group_id)
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("exp:view:"))
async def handle_view_single_expense(callback: CallbackQuery):
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
        await callback.answer("هزینه یافت نشد!", show_alert=True)
        return

    status = "تسویه شده ✅" if expense.get("settled") else "فعال در دوره جاری ⏳"
    text = (
        f"🔍 <b>جزئیات هزینه:</b>\n\n"
        f"🏷️ بابت: <b>{expense['title']}</b>\n"
        f"💰 مبلغ: <b>{format_amount(expense['amount'])}</b>\n"
        f"👤 پرداخت‌کننده: <b>{expense.get('payer_name', 'نامشخص')}</b>\n"
        f"📅 تاریخ: {expense.get('created_at', '')}\n"
        f"📊 وضعیت: <b>{status}</b>\n"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.single_expense_keyboard(exp_id, group_id)
    )


@router.callback_query(F.data.startswith("exp:del:"))
async def handle_delete_expense(callback: CallbackQuery):
    parts = callback.data.split(":")
    exp_id = int(parts[2])
    group_id = int(parts[3])
    
    success = await db.delete_expense(exp_id, group_id)
    if success:
        await callback.answer("✅ هزینه با موفقیت حذف شد.", show_alert=True)
    else:
        await callback.answer("⚠️ خطا در حذف هزینه!", show_alert=True)
        
    # بازگشت به تاریخچه
    history = await db.get_group_history(group_id, limit=15)
    group = await db.get_group_by_id(group_id)
    if not history:
        text = f"📜 هنوز هیچ هزینه‌ای برای گروه <b>«{group['title']}»</b> ثبت نشده است."
        markup = kb.InlineKeyboardMarkup(inline_keyboard=[
            [kb.InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    else:
        text = f"📜 <b>تاریخچه هزینه‌های گروه «{group['title']}»:</b>"
        markup = kb.expense_history_keyboard(history, group_id)
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
