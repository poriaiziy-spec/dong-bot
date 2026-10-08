from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import ShoppingItemStates, ExpenseCreationStates
from helpers import clean_amount_input, format_amount, safe, parse_quantity, format_quantity
from tones import msg_expense_payer_prompt

router = Router()

@router.callback_query(F.data.startswith("shop:view:"))
async def handle_shopping_view(callback: CallbackQuery, state: FSMContext = None):
    if state:
        await state.clear()
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.message.edit_text("⚠️ این گروه یافت نشد.", reply_markup=kb.main_menu_keyboard())
        return

    items = await db.get_group_shopping_items(group_id)
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"

    if not items:
        text = (
            f"🛒 <b>لیست خرید و فاکتور ساز دورهمی «{safe(group['title'])}»</b> 🧾✨\n\n"
            f"{safe(calling_name)} قشنگم، اینجا می‌تونی اقلام خرید رو دونه‌دونه با <b>قیمت واحد</b> و <b>تعداد</b> ثبت کنی تا برات جمع کل رو خودکار و دقیق حساب کنم!\n\n"
            "📝 هنوز هیچ قلم خریدی ثبت نشده عزیز دلم.\n"
            "با دکمه زیر اولین قلم خرید رو اضافه کن:"
        )
        markup = kb.shopping_list_keyboard(group_id, has_items=False)
    else:
        lines = [
            f"🛒 <b>لیست خرید و فاکتور ساز دورهمی «{safe(group['title'])}»</b> 🧾✨\n",
            f"{safe(calling_name)} جانم، اقلام ثبت‌شده تا الان به شرح زیر است:\n"
        ]
        total_sum = 0
        for idx, it in enumerate(items, 1):
            total_sum += it["total_price"]
            u_name = it.get("calling_name") or it.get("full_name") or "هم‌گروهی"
            qty_str = format_quantity(it["quantity"])
            unit_str = format_amount(it["unit_price"])
            tot_str = format_amount(it["total_price"])
            lines.append(
                f"{idx}. <b>{safe(it['item_name'])}</b>\n"
                f"   • فی واحد: {unit_str} | تعداد: {qty_str}\n"
                f"   💰 <b>جمع این قلم: {tot_str}</b>  <i>(ثبت: {safe(u_name)})</i>\n"
            )
        lines.append("────────────────────────")
        lines.append(f"💳 <b>جمع کل فاکتور خرید: {format_amount(total_sum)}</b> ({len(items)} قلم کالا)")
        text = "\n".join(lines)
        markup = kb.shopping_list_keyboard(group_id, has_items=True)

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("shop:add:"))
async def handle_shopping_add_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.message.edit_text("⚠️ گروه یافت نشد.", reply_markup=kb.main_menu_keyboard())
        return

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    await state.clear()
    await state.set_state(ShoppingItemStates.waiting_for_name)
    await state.update_data(group_id=group_id)

    text = (
        "🛒 <b>افزودن قلم خرید جدید</b>\n\n"
        f"{safe(calling_name)} قشنگم، لطفاً <b>نام یا عنوان کالا</b> رو برام بنویس:\n"
        "<i>(مثلاً: <code>چیپس</code>، <code>نوشابه</code>، <code>گوشت</code>، <code>بنزین</code>)</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.message(ShoppingItemStates.waiting_for_name)
async def handle_shopping_item_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")

    raw_text = (message.text or "").strip()
    if len(raw_text) < 1 or len(raw_text) > 80:
        sent = await message.answer(
            f"⚠️ {safe(calling_name)} جانم، لطفاً نام کالا را بین ۱ تا ۸۰ کاراکتر وارد کن:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
            ])
        )
        await db.record_chat_message(user_id, sent.message_id)
        try:
            await message.delete()
        except Exception:
            pass
        return

    # بررسی هوشمند ورود یکجا: مثلا «چیپس 35000 4»
    parts = raw_text.split()
    if len(parts) >= 3:
        potential_qty = parse_quantity(parts[-1])
        potential_unit = clean_amount_input(parts[-2])
        if potential_qty and potential_unit and potential_qty > 0 and potential_unit > 0:
            name_part = " ".join(parts[:-2]).strip()
            if name_part:
                await db.add_shopping_item(group_id, user_id, name_part, potential_unit, potential_qty)
                await state.clear()
                await db.cleanup_chat_history(message.bot, user_id)
                tot = int(round(potential_unit * potential_qty))
                sent = await message.answer(
                    f"✅ <b>«{safe(name_part)}» با موفقیت به فاکتور خرید اضافه شد {safe(calling_name)} جانم!</b> 🌸\n\n"
                    f"• فی واحد: {format_amount(potential_unit)}\n"
                    f"• تعداد / مقدار: <b>{format_quantity(potential_qty)}</b>\n"
                    f"💰 <b>قیمت کل این قلم: {format_amount(tot)}</b>",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="➕ افزودن قلم بعدی", callback_data=f"shop:add:{group_id}")],
                        [InlineKeyboardButton(text="🧾 مشاهده فاکتور خرید", callback_data=f"shop:view:{group_id}")]
                    ])
                )
                await db.record_chat_message(user_id, sent.message_id)
                try:
                    await message.delete()
                except Exception:
                    pass
                return

    await state.update_data(item_name=raw_text)
    await state.set_state(ShoppingItemStates.waiting_for_unit_price)
    await db.cleanup_chat_history(message.bot, user_id)

    prompt_text = (
        f"🏷️ قلم خرید: <b>«{safe(raw_text)}»</b>\n\n"
        f"💵 <b>قیمت واحد (فی هر یک عدد)</b> چقدره {safe(calling_name)} قشنگم؟\n"
        "لطفاً مبلغ رو به <b>تومان</b> برام بفرست:\n"
        "<i>(مثلاً: <code>35000</code> یا <code>۳۵ هزار</code> یا <code>35k</code>)</i>"
    )
    sent = await message.answer(
        prompt_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.message(ShoppingItemStates.waiting_for_unit_price)
async def handle_shopping_unit_price(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")
    item_name = data.get("item_name", "کالا")

    unit_price = clean_amount_input(message.text)
    if not unit_price or unit_price <= 0:
        sent = await message.answer(
            f"⚠️ مبلغ قیمت واحد نامعتبر است {safe(calling_name)} قشنگم! لطفاً عددی به تومان بفرست (مثلاً: <code>35000</code> یا <code>۳۵ هزار</code>):",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
            ])
        )
        await db.record_chat_message(user_id, sent.message_id)
        try:
            await message.delete()
        except Exception:
            pass
        return

    await state.update_data(unit_price=unit_price)
    await state.set_state(ShoppingItemStates.waiting_for_quantity)
    await db.cleanup_chat_history(message.bot, user_id)

    prompt_text = (
        f"🏷️ قلم خرید: <b>«{safe(item_name)}»</b>\n"
        f"💵 قیمت واحد: <b>{format_amount(unit_price)}</b>\n\n"
        f"🔢 <b>تعداد یا مقدارش</b> چنده {safe(calling_name)} جانم؟\n"
        "<i>(مثلاً: <code>4</code> یا <code>۲</code> یا حتی اعشاری مثل <code>1.5</code>)</i>"
    )
    sent = await message.answer(
        prompt_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.message(ShoppingItemStates.waiting_for_quantity)
async def handle_shopping_quantity(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")
    item_name = data.get("item_name", "کالا")
    unit_price = data.get("unit_price", 0)

    qty = parse_quantity(message.text)
    if not qty or qty <= 0:
        sent = await message.answer(
            f"⚠️ مقدار یا تعداد نامعتبر است {safe(calling_name)} قشنگم! لطفاً عددی مانند <code>4</code> یا <code>1.5</code> بفرست:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
            ])
        )
        await db.record_chat_message(user_id, sent.message_id)
        try:
            await message.delete()
        except Exception:
            pass
        return

    total_price = int(round(unit_price * qty))
    await db.add_shopping_item(group_id, user_id, item_name, unit_price, qty)
    await state.clear()
    await db.cleanup_chat_history(message.bot, user_id)

    success_text = (
        f"✅ <b>«{safe(item_name)}» با عشق به فاکتور خرید اضافه شد {safe(calling_name)} جانم!</b> 🌸❤️\n\n"
        f"• قیمت واحد (فی): {format_amount(unit_price)}\n"
        f"• تعداد / مقدار: <b>{format_quantity(qty)}</b>\n"
        f"💰 <b>قیمت کل این قلم: {format_amount(total_price)}</b>\n\n"
        "می‌تونی قلم بعدی رو اضافه کنی یا لیست کامل فاکتور رو ببینی:"
    )
    sent = await message.answer(
        success_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ افزودن قلم بعدی", callback_data=f"shop:add:{group_id}")],
            [InlineKeyboardButton(text="🧾 مشاهده فاکتور خرید", callback_data=f"shop:view:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("shop:del_menu:"))
async def handle_shopping_del_menu(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    items = await db.get_group_shopping_items(group_id)
    if not items:
        await callback.answer("لیست خرید خالی است!", show_alert=True)
        return

    await callback.answer()
    text = "🗑️ <b>حذف قلم از فاکتور خرید:</b>\n\nروی هر قلمی که می‌خوای حذف بشه بزن عزیز دلم:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.shopping_del_items_keyboard(items, group_id))


@router.callback_query(F.data.startswith("shop:del_do:"))
async def handle_shopping_del_do(callback: CallbackQuery):
    parts = callback.data.split(":")
    item_id = int(parts[2])
    group_id = int(parts[3])

    await db.delete_shopping_item(item_id, group_id)
    await callback.answer("✅ این قلم با موفقیت حذف شد جان دلم.", show_alert=True)
    # بازگشت به نمایش فاکتور
    await handle_shopping_view(callback)


@router.callback_query(F.data.startswith("shop:clear_confirm:"))
async def handle_shopping_clear_confirm(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    text = (
        "⚠️ <b>خالی کردن کل لیست خرید</b>\n\n"
        "کاملاً مطمئنی که می‌خوای تمام اقلام فاکتور خرید پاک بشن عزیز دلم؟ ☕💔"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.shopping_clear_confirm_keyboard(group_id))


@router.callback_query(F.data.startswith("shop:clear_do:"))
async def handle_shopping_clear_do(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    await db.clear_group_shopping_items(group_id)
    await callback.answer("🧹 تمام اقلام فاکتور خرید پاک شدند جان دلم.", show_alert=True)
    await handle_shopping_view(callback)


@router.callback_query(F.data.startswith("shop:to_exp:"))
async def handle_shopping_to_expense(callback: CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split(":")[2])
    items = await db.get_group_shopping_items(group_id)
    if not items:
        await callback.answer("⚠️ هنوز هیچ قلم خریدی برای ثبت وجود ندارد!", show_alert=True)
        return

    await callback.answer()
    total_amount = sum(it["total_price"] for it in items)
    title = f"خرید اقلام فاکتور ({len(items)} قلم)"
    tone = await db.get_group_tone(group_id)
    members = await db.get_group_members(group_id)

    await state.clear()
    await state.set_state(ExpenseCreationStates.waiting_for_payer)
    await state.update_data(
        group_id=group_id,
        title=title,
        amount=total_amount,
        tone=tone,
        from_shopping_list=True
    )

    text = msg_expense_payer_prompt(tone, title, format_amount(total_amount))
    markup = kb.payer_select_keyboard(group_id, members, callback.from_user.id)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
