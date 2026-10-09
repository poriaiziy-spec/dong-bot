import math
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import ShoppingItemStates, ExpenseCreationStates
from helpers import clean_amount_input, format_amount, safe, parse_quantity, format_quantity, parse_bulk_shopping_text, parse_single_shopping_line
from tones import msg_expense_payer_prompt

router = Router()


def _extract_item_and_qty(raw_text: str) -> tuple[str, float]:
    """استخراج هوشمند نام قلم و مقدار از متن، مانند: 'شیر ۲ تا' یا 'سیب زمینی ۳ کیلو'"""
    parts = raw_text.split()
    if len(parts) >= 2:
        # بررسی پسوندهای رایج فارسی مانند '۲ تا'، '۳ عدد'، '۱.۵ کیلو'، '۲ بسته'
        last = parts[-1]
        prev = parts[-2]
        if last in ["تا", "عدد", "کیلو", "بسته", "دانه", "بطری", "جعبه"]:
            qty = parse_quantity(prev)
            if qty and qty > 0:
                name = " ".join(parts[:-2]).strip()
                if name:
                    return name, qty
        # یا اگر کلمه آخر مستقیما عدد باشد: 'شیر 2'
        qty = parse_quantity(last)
        if qty and qty > 0:
            name = " ".join(parts[:-1]).strip()
            if name:
                return name, qty
    return raw_text.strip(), 1.0


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
            f"🛒 <b>لیست خریدهای خونه و مایحتاج دورهمی «{safe(group['title'])}»</b> 🧺✨\n\n"
            f"{safe(calling_name)} قشنگم، اینجا لیست اقلامی است که بچه‌های گروه مشخص کردن باید خریده بشه.\n\n"
            "📝 <b>در حال حاضر هیچ قلم خریدی در لیست نیست عزیز دلم.</b>\n"
            "هر چیزی که لازمه خریده بشه رو با دکمه زیر به لیست اضافه کن تا فراموش نشه:\n"
            "<i>(نکته: نیازی به دانستن قیمت نیست؛ موقع خرید مبلغ وارد می‌شود!)</i>"
        )
        markup = kb.shopping_list_keyboard(group_id, has_items=False)
    else:
        lines = [
            f"🛒 <b>لیست خریدهای خونه و مایحتاج «{safe(group['title'])}»</b> 🧺✨\n",
            f"{safe(calling_name)} جانم، اقلام مورد نیاز برای خرید به شرح زیر است:\n"
        ]
        total_sum = 0
        has_priced_items = False
        for idx, it in enumerate(items, 1):
            u_name = it.get("calling_name") or it.get("full_name") or "هم‌گروهی"
            qty_str = format_quantity(it["quantity"])
            tot_price = it.get("total_price", 0)
            
            if tot_price > 0:
                has_priced_items = True
                total_sum += tot_price
                unit_str = format_amount(it.get("unit_price", 0))
                tot_str = format_amount(tot_price)
                lines.append(
                    f"{idx}. 💰 <b>{safe(it['item_name'])}</b>\n"
                    f"   • فی: {unit_str} | مقدار: {qty_str} ➔ <b>جمع: {tot_str}</b>\n"
                    f"   <i>(پیشنهاد: {safe(u_name)})</i>\n"
                )
            else:
                lines.append(
                    f"{idx}. ⭕ <b>{safe(it['item_name'])}</b> (مقدار: <b>{qty_str}</b>)\n"
                    f"   <i>(پیشنهاد: {safe(u_name)})</i>\n"
                )

        lines.append("────────────────────────")
        lines.append(f"📌 <b>{len(items)} قلم کالا در انتظار خرید</b>")
        if has_priced_items and total_sum > 0:
            lines.append(f"💳 جمع اقلام دارای قیمت تخمینی: {format_amount(total_sum)}")

        bought_items = await db.get_bought_shopping_items(group_id, limit=5)
        if bought_items:
            lines.append("\n✅ <b>اقلام خریداری‌شده اخیر:</b>")
            for b in bought_items:
                b_name = b.get("buyer_calling") or b.get("buyer_name") or "هم‌گروهی"
                b_qty = format_quantity(b.get("quantity", 1))
                lines.append(f"• <s>{safe(b['item_name'])}</s> ({b_qty}) • <i>خریدار: {safe(b_name)}</i>")

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
        "🛒 <b>افزودن به خریدهای خونه / لیست مایحتاج</b> 🧺✨\n\n"
        f"{safe(calling_name)} قشنگم، چه چیزی باید برای خونه یا دورهمی خریده بشه؟\n"
        "نام کالا و در صورت تمایل مقدارش رو برام بنویس:\n"
        "<i>(مثلاً: <code>شیر ۲ تا</code>، <code>روغن مایع</code>، <code>دستمال کاغذی</code>، <code>سیب زمینی ۳ کیلو</code>)</i>\n\n"
        "💡 <i>نیازی به وارد کردن قیمت در این مرحله نیست! هر کسی که رفت خرید، تیک قلم رو می‌زنه و مبلغش رو ثبت می‌کنه تا دنگ حساب بشه.</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("shop:bulk:"))
async def handle_shopping_bulk_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.message.edit_text("⚠️ گروه یافت نشد.", reply_markup=kb.main_menu_keyboard())
        return

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    await state.clear()
    await state.set_state(ShoppingItemStates.waiting_for_bulk_text)
    await state.update_data(group_id=group_id)

    text = (
        "📝 <b>افزودن دسته‌ای اقلام به لیست خریدهای خونه</b> 🧺✨\n\n"
        f"{safe(calling_name)} قشنگم، کل لیست خریدت رو برام بفرست!\n\n"
        "می‌تونی اقلام رو زیر هم بنویسی، شماره‌گذاری کنی یا با ویرگول (،) جدا کنی.\n"
        "حتی اگر تعداد یا قیمت هم بنویسی متوجه میشم:\n\n"
        "📋 <b>چند نمونه ورودی:</b>\n"
        "• <code>شیر ۲ تا\nنان سنگک\nپنیر\nروغن ۴۵۰۰۰ ۲\nتخم‌مرغ ۱ شانه</code>\n\n"
        "• یا در یک خط:\n"
        "<code>شیر، ماست، پنیر، نان سنگک ۲ تا</code>\n\n"
        "<i>منتظر لیست قشنگتم... ✨</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data=f"shop:view:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.message(ShoppingItemStates.waiting_for_bulk_text)
async def handle_shopping_bulk_submit(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")

    raw_text = (message.text or "").strip()
    items = parse_bulk_shopping_text(raw_text)

    if not items:
        sent = await message.answer(
            f"⚠️ {safe(calling_name)} جانم، متوجه قلمی در این متن نشدم! لطفاً لیست خرید را با نام اقلام بفرست:\n"
            "<i>(مثلاً:\nشیر ۲ تا\nنان سنگک\nپنیر)</i>",
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

    inserted_ids = await db.add_shopping_items_bulk(group_id, user_id, items)
    await state.clear()
    await db.cleanup_chat_history(message.bot, user_id)

    item_lines = []
    total_priced = 0
    for idx, it in enumerate(items, 1):
        q_str = f" ({format_quantity(it['quantity'])})" if it["quantity"] != 1.0 else ""
        if it["total_price"] > 0:
            total_priced += it["total_price"]
            item_lines.append(f"{idx}. 💰 <b>{safe(it['item_name'])}</b>{q_str} ➔ {format_amount(it['total_price'])}")
        else:
            item_lines.append(f"{idx}. ⭕ <b>{safe(it['item_name'])}</b>{q_str}")

    summary_text = (
        f"✅ <b>{len(inserted_ids)} قلم کالا با موفقیت به لیست خریدهای خونه اضافه شد {safe(calling_name)} جانم!</b> 🧺🌸\n\n"
        + "\n".join(item_lines) + "\n\n"
    )
    if total_priced > 0:
        summary_text += f"💳 جمع اقلام دارای قیمت: <b>{format_amount(total_priced)}</b>\n\n"

    summary_text += "هر موقع خرید انجام شد، با دکمه «🛍️ من خریدم» می‌تونید اقلام خریداری‌شده رو تیک بزنید تا دنگشون حساب بشه."

    sent = await message.answer(
        summary_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ افزودن قلم تک", callback_data=f"shop:add:{group_id}"),
                InlineKeyboardButton(text="📝 افزودن لیست دیگر", callback_data=f"shop:bulk:{group_id}")
            ],
            [InlineKeyboardButton(text="📋 مشاهده لیست خریدهای خونه", callback_data=f"shop:view:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.message(ShoppingItemStates.waiting_for_name)
async def handle_shopping_item_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")

    raw_text = (message.text or "").strip()

    # بررسی هوشمند ورود لیست چند قلمی در فرم تک‌قلمی
    bulk_items = parse_bulk_shopping_text(raw_text)
    if len(bulk_items) > 1:
        inserted_ids = await db.add_shopping_items_bulk(group_id, user_id, bulk_items)
        await state.clear()
        await db.cleanup_chat_history(message.bot, user_id)

        item_lines = []
        total_priced = 0
        for idx, it in enumerate(bulk_items, 1):
            q_str = f" ({format_quantity(it['quantity'])})" if it["quantity"] != 1.0 else ""
            if it["total_price"] > 0:
                total_priced += it["total_price"]
                item_lines.append(f"{idx}. 💰 <b>{safe(it['item_name'])}</b>{q_str} ➔ {format_amount(it['total_price'])}")
            else:
                item_lines.append(f"{idx}. ⭕ <b>{safe(it['item_name'])}</b>{q_str}")

        summary_text = (
            f"✅ <b>{len(inserted_ids)} قلم کالا به صورت دسته‌ای به لیست خریدهای خونه اضافه شد {safe(calling_name)} جانم!</b> 🧺🌸\n\n"
            + "\n".join(item_lines) + "\n\n"
        )
        if total_priced > 0:
            summary_text += f"💳 جمع اقلام دارای قیمت: <b>{format_amount(total_priced)}</b>\n\n"

        summary_text += "هر موقع خرید انجام شد، با دکمه «🛍️ من خریدم» می‌تونید اقلام خریداری‌شده رو تیک بزنید تا دنگشون حساب بشه."

        sent = await message.answer(
            summary_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="➕ افزودن قلم تک", callback_data=f"shop:add:{group_id}"),
                    InlineKeyboardButton(text="📝 افزودن لیست دیگر", callback_data=f"shop:bulk:{group_id}")
                ],
                [InlineKeyboardButton(text="📋 مشاهده لیست خریدهای خونه", callback_data=f"shop:view:{group_id}")]
            ])
        )
        await db.record_chat_message(user_id, sent.message_id)
        try:
            await message.delete()
        except Exception:
            pass
        return

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

    # بررسی هوشمند ورود کامل فاکتور: مثلا «چیپس 35000 4»
    parts = raw_text.split()
    if len(parts) >= 3:
        potential_qty = parse_quantity(parts[-1])
        potential_unit = clean_amount_input(parts[-2])
        if potential_qty and potential_unit and potential_qty > 0 and potential_unit > 0:
            name_part = " ".join(parts[:-2]).strip()
            if name_part:
                it_id = await db.add_shopping_item(group_id, user_id, name_part, potential_unit, potential_qty)
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
                        [InlineKeyboardButton(text="📋 مشاهده لیست خریدهای خونه", callback_data=f"shop:view:{group_id}")]
                    ])
                )
                await db.record_chat_message(user_id, sent.message_id)
                try:
                    await message.delete()
                except Exception:
                    pass
                return

    # استخراج نام و مقدار (بدون قیمت، برای لیست خریدهای خونه)
    item_name, qty = _extract_item_and_qty(raw_text)
    it_id = await db.add_shopping_item(group_id, user_id, item_name, 0, qty)
    await state.clear()
    await db.cleanup_chat_history(message.bot, user_id)

    qty_text = f" ({format_quantity(qty)})" if qty != 1.0 else ""
    success_text = (
        f"✅ <b>«{safe(item_name)}{qty_text}» با موفقیت به لیست خریدهای خونه اضافه شد {safe(calling_name)} جانم!</b> 🧺🌸\n\n"
        "هر موقع هر کدوم از بچه‌ها این قلم یا اقلام دیگه رو خرید، کافیه روی دکمه «🛍️ من خریدم / ثبت دنگ» بزنه تا با مشخص کردن خریدهایش، دنگ آن خودکار حساب بشه."
    )
    sent = await message.answer(
        success_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ افزودن قلم بعدی به لیست", callback_data=f"shop:add:{group_id}")],
            [InlineKeyboardButton(text="💵 ثبت قیمت برای این قلم", callback_data=f"shop:set_price:{it_id}:{group_id}")],
            [InlineKeyboardButton(text="📋 مشاهده لیست خریدهای خونه", callback_data=f"shop:view:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.callback_query(F.data.startswith("shop:set_price:"))
async def handle_shopping_set_price_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    item_id = int(parts[2])
    group_id = int(parts[3])

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    await state.clear()
    await state.set_state(ShoppingItemStates.waiting_for_unit_price)
    await state.update_data(item_id=item_id, group_id=group_id)

    text = (
        f"💵 <b>ثبت قیمت برای قلم خرید</b>\n\n"
        f"قیمت واحد این قلم چقدره {safe(calling_name)} قشنگم؟ لطفاً مبلغ را به تومان بفرست:\n"
        "<i>(مثلاً: <code>45000</code> یا <code>۴۵ هزار</code>)</i>"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
    ]))


@router.message(ShoppingItemStates.waiting_for_unit_price)
async def handle_shopping_unit_price(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")
    item_id = data.get("item_id")
    item_name = data.get("item_name", "کالا")

    unit_price = clean_amount_input(message.text)
    if not unit_price or unit_price <= 0:
        sent = await message.answer(
            f"⚠️ مبلغ قیمت واحد نامعتبر است {safe(calling_name)} قشنگم! لطفاً عددی به تومان بفرست (مثلاً: <code>35000</code>):",
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
        f"💵 قیمت واحد: <b>{format_amount(unit_price)}</b>\n\n"
        f"🔢 <b>تعداد یا مقدارش</b> چنده {safe(calling_name)} جانم؟\n"
        "<i>(مثلاً: <code>4</code> یا <code>۲</code> یا <code>1.5</code>)</i>"
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
    item_id = data.get("item_id")
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
    if item_id:
        async with aiosqlite_connect() as conn:
            await conn.execute(
                "UPDATE shopping_items SET unit_price = ?, quantity = ?, total_price = ? WHERE id = ? AND group_id = ?",
                (unit_price, qty, total_price, item_id, group_id)
            )
            await conn.commit()
    else:
        item_name = data.get("item_name", "کالا")
        await db.add_shopping_item(group_id, user_id, item_name, unit_price, qty)

    await state.clear()
    await db.cleanup_chat_history(message.bot, user_id)

    success_text = (
        f"✅ <b>قیمت با موفقیت ثبت شد {safe(calling_name)} جانم!</b> 🌸❤️\n\n"
        f"• فی واحد: {format_amount(unit_price)}\n"
        f"• مقدار: <b>{format_quantity(qty)}</b>\n"
        f"💰 <b>قیمت کل این قلم: {format_amount(total_price)}</b>"
    )
    sent = await message.answer(
        success_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ افزودن قلم بعدی", callback_data=f"shop:add:{group_id}")],
            [InlineKeyboardButton(text="📋 مشاهده لیست خریدهای خونه", callback_data=f"shop:view:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


def aiosqlite_connect():
    import aiosqlite
    from config import DB_PATH
    return aiosqlite.connect(DB_PATH)


# ===========================================================================
# فرآیند خرید، انتخاب اقلام و محاسبه دنگ
# ===========================================================================

@router.callback_query(F.data.startswith("shop:bmenu:"))
async def handle_shopping_buy_menu(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    items = await db.get_group_shopping_items(group_id)
    if not items:
        await callback.answer("⚠️ لیست خرید خالی است عزیز دلم!", show_alert=True)
        return

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    await state.clear()
    await state.update_data(group_id=group_id, selected_ids=[])

    text = (
        f"🛍️ <b>کدوم قلم‌ها رو خریدی {safe(calling_name)} جانم؟</b> 🧺✨\n\n"
        "روی هر قلمی که خریدی بزن تا تیک بخوره (✅)، سپس دکمه <b>«تایید و ثبت مبلغ»</b> رو بزن تا مبلغ هرکدوم رو بپرسم و دنگش رو حساب کنم:"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.shopping_buy_items_keyboard(items, group_id, set())
    )


@router.callback_query(F.data.startswith("shop:btog:"))
async def handle_shopping_buy_toggle(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    group_id = int(parts[2])
    item_id = int(parts[3])

    data = await state.get_data()
    selected = set(data.get("selected_ids", []))
    if item_id in selected:
        selected.remove(item_id)
    else:
        selected.add(item_id)

    await state.update_data(selected_ids=list(selected))
    items = await db.get_group_shopping_items(group_id)

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    text = (
        f"🛍️ <b>کدوم قلم‌ها رو خریدی {safe(calling_name)} جانم؟</b> 🧺✨\n\n"
        f"تعداد انتخاب شده: <b>{len(selected)} قلم</b>\n"
        "روی اقلام ضربه بزن تا تغییر کنه، بعد تایید رو بزن:"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.shopping_buy_items_keyboard(items, group_id, selected)
    )


@router.callback_query(F.data.startswith("shop:ball:"))
async def handle_shopping_buy_all(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    items = await db.get_group_shopping_items(group_id)
    all_ids = [it["id"] for it in items]
    await state.update_data(selected_ids=all_ids)

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    text = (
        f"🛍️ <b>تمام {len(all_ids)} قلم انتخاب شدند {safe(calling_name)} جانم!</b> 🧺✨\n\n"
        "حالا دکمه «تایید و ثبت مبلغ» رو بزن تا مبالغ رو وارد کنی:"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.shopping_buy_items_keyboard(items, group_id, set(all_ids))
    )


@router.callback_query(F.data.startswith("shop:bnone:"))
async def handle_shopping_buy_none(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    items = await db.get_group_shopping_items(group_id)
    await state.update_data(selected_ids=[])

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    text = (
        f"🛍️ <b>کدوم قلم‌ها رو خریدی {safe(calling_name)} جانم؟</b> 🧺✨\n\n"
        "روی هر قلمی که خریدی ضربه بزن تا تیک بخوره:"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.shopping_buy_items_keyboard(items, group_id, set())
    )


@router.callback_query(F.data.startswith("shop:bconf:"))
async def handle_shopping_buy_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    selected_ids = data.get("selected_ids", [])
    if not selected_ids:
        await callback.answer("⚠️ لطفاً حداقل یک قلم را انتخاب کن عزیز دلم!", show_alert=True)
        return

    items = await db.get_group_shopping_items(group_id)
    items_to_price = [it for it in items if it["id"] in selected_ids]
    if not items_to_price:
        await callback.answer("⚠️ اقلام انتخابی یافت نشدند!", show_alert=True)
        return

    buyer_id = callback.from_user.id
    calling_name = await db.get_user_calling_name(buyer_id) or "جان دلم"

    await state.set_state(ShoppingItemStates.waiting_for_item_price_batch)
    await state.update_data(
        group_id=group_id,
        buyer_id=buyer_id,
        items_to_price=items_to_price,
        current_idx=0,
        collected_prices={}
    )

    first_item = items_to_price[0]
    qty_str = format_quantity(first_item["quantity"])
    text = (
        f"🧾 <b>مرحله ۱ از {len(items_to_price)}: ثبت مبلغ خرید</b>\n\n"
        f"{safe(calling_name)} قشنگم، لطفاً مبلغ پرداختی برای <b>«{safe(first_item['item_name'])}»</b> ({qty_str}) را به <b>تومان</b> بفرست:\n"
        "<i>(مثلاً: <code>45000</code> یا <code>۴۵ هزار</code> یا <code>45k</code>)</i>\n\n"
        "💡 <i>اگر یک فاکتور کلی داری، می‌تونی با دکمه زیر کل مبلغ را یکجا وارد کنی:</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧾 ثبت یکجای کل فاکتور برای تمام اقلام", callback_data=f"shop:blump:{group_id}")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("shop:blump:"))
async def handle_shopping_buy_lump_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    data = await state.get_data()
    items = data.get("items_to_price", [])

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    await state.set_state(ShoppingItemStates.waiting_for_lump_sum)

    text = (
        f"🧾 <b>ثبت یکجای مبلغ خرید {len(items)} قلم</b> 🛒✨\n\n"
        f"{safe(calling_name)} جانم، لطفاً <b>مبلغ کل تمام اقلام خریداری‌شده</b> را به تومان بفرست:\n"
        "<i>(مثلاً: <code>180000</code> یا <code>۱۸۰ هزار</code>)</i>"
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.message(ShoppingItemStates.waiting_for_lump_sum)
async def handle_shopping_lump_sum(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")
    buyer_id = data.get("buyer_id", user_id)
    items_to_price = data.get("items_to_price", [])

    total_amount = clean_amount_input(message.text)
    if not total_amount or total_amount <= 0:
        sent = await message.answer(
            f"⚠️ مبلغ وارد شده نامعتبر است {safe(calling_name)} قشنگم! لطفاً عددی به تومان بفرست (مثلاً: <code>180000</code>):",
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

    # ثبت به عنوان هزینه گروه و تقسیم دنگ
    members = await db.get_group_members(group_id)
    if not members:
        members = [{"id": buyer_id}]

    m_count = len(members)
    base_share = total_amount // m_count
    rem = total_amount % m_count
    shares = {}
    for idx, m in enumerate(members):
        shares[m["id"]] = base_share + (1 if idx < rem else 0)

    names_summary = "، ".join(it["item_name"] for it in items_to_price)
    title = f"خرید خونه ({names_summary[:36]})"

    exp_id = await db.add_expense(group_id, buyer_id, title, total_amount, shares)
    del_ids = [it["id"] for it in items_to_price]
    await db.mark_shopping_items_bought(del_ids, buyer_id)

    await state.clear()
    await db.cleanup_chat_history(message.bot, user_id)

    buyer_name = await db.get_user_calling_name(buyer_id) or "خریدار محترم"
    receipt_text = (
        f"🎉 <b>خرید خونه با موفقیت ثبت شد و دنگ آن محاسبه گردید!</b> 🧾✨\n\n"
        f"🛍️ <b>اقلام خریداری‌شده ({len(items_to_price)} قلم):</b>\n"
        + "".join(f"• {safe(it['item_name'])} ({format_quantity(it['quantity'])})\n" for it in items_to_price)
        + f"\n💰 <b>مجموع کل فاکتور: {format_amount(total_amount)}</b>\n"
        f"👤 <b>خریدار:</b> {safe(buyer_name)}\n"
        f"👥 <b>سهم هر یک از اعضا ({m_count} نفر):</b> <b>{format_amount(base_share)}</b>\n\n"
        "🌸 <i>اقلام خریداری‌شده به عنوان خریدهای انجام‌شده علامت خوردند. دست خریدار پر برکت!</i> ❤️"
    )
    sent = await message.answer(
        receipt_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 اطلاع‌رسانی خرید به اعضای گروه", callback_data=f"shop:bnotif:{exp_id}:{group_id}")],
            [InlineKeyboardButton(text="🛒 مشاهده لیست خریدهای خونه", callback_data=f"shop:view:{group_id}")],
            [InlineKeyboardButton(text="📊 وضعیت حساب‌ها و تراز مالی", callback_data=f"grp:report:{group_id}")],
            [InlineKeyboardButton(text="🏠 بازگشت به منوی دورهمی", callback_data=f"grp:view:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)
    try:
        await message.delete()
    except Exception:
        pass


@router.message(ShoppingItemStates.waiting_for_item_price_batch)
async def handle_shopping_item_price_batch(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    group_id = data.get("group_id")
    buyer_id = data.get("buyer_id", user_id)
    items_to_price = data.get("items_to_price", [])
    current_idx = data.get("current_idx", 0)
    collected_prices = data.get("collected_prices", {})

    amount = clean_amount_input(message.text)
    if not amount or amount <= 0:
        sent = await message.answer(
            f"⚠️ مبلغ وارد شده نامعتبر است {safe(calling_name)} قشنگم! لطفاً عددی به تومان بفرست (مثلاً: <code>45000</code>):",
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

    current_item = items_to_price[current_idx]
    collected_prices[str(current_item["id"])] = amount
    current_idx += 1

    await state.update_data(current_idx=current_idx, collected_prices=collected_prices)
    await db.cleanup_chat_history(message.bot, user_id)
    try:
        await message.delete()
    except Exception:
        pass

    if current_idx < len(items_to_price):
        # قلم بعدی
        next_item = items_to_price[current_idx]
        next_qty = format_quantity(next_item["quantity"])
        prompt_text = (
            f"🧾 <b>مرحله {current_idx + 1} از {len(items_to_price)}: ثبت مبلغ خرید</b>\n\n"
            f"حالا مبلغ پرداختی برای <b>«{safe(next_item['item_name'])}»</b> ({next_qty}) را به <b>تومان</b> بفرست {safe(calling_name)} جانم:\n"
            "<i>(مثلاً: <code>35000</code> یا <code>۳۵ هزار</code>)</i>"
        )
        sent = await message.answer(
            prompt_text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:view:{group_id}")]
            ])
        )
        await db.record_chat_message(user_id, sent.message_id)
        return

    # تمام اقلام قیمت‌گذاری شدند! محاسبه جمع کل و ثبت دنگ
    total_amount = sum(collected_prices.values())
    members = await db.get_group_members(group_id)
    if not members:
        members = [{"id": buyer_id}]

    m_count = len(members)
    base_share = total_amount // m_count
    rem = total_amount % m_count
    shares = {}
    for idx, m in enumerate(members):
        shares[m["id"]] = base_share + (1 if idx < rem else 0)

    names_summary = "، ".join(it["item_name"] for it in items_to_price)
    title = f"خرید خونه ({names_summary[:36]})"

    exp_id = await db.add_expense(group_id, buyer_id, title, total_amount, shares)
    del_ids = [it["id"] for it in items_to_price]
    await db.mark_shopping_items_bought(del_ids, buyer_id)

    await state.clear()

    buyer_name = await db.get_user_calling_name(buyer_id) or "خریدار محترم"
    item_rows = ""
    for it in items_to_price:
        p = collected_prices.get(str(it["id"]), 0)
        item_rows += f"• {safe(it['item_name'])} ({format_quantity(it['quantity'])}): <b>{format_amount(p)}</b>\n"

    receipt_text = (
        f"🎉 <b>خرید خونه با موفقیت ثبت شد و دنگ آن بین اعضا محاسبه گردید!</b> 🧾✨\n\n"
        f"🛍️ <b>اقلام خریداری‌شده:</b>\n"
        f"{item_rows}\n"
        f"💰 <b>مجموع کل فاکتور: {format_amount(total_amount)}</b>\n"
        f"👤 <b>خریدار:</b> {safe(buyer_name)}\n"
        f"👥 <b>سهم هر یک از اعضا ({m_count} نفر):</b> <b>{format_amount(base_share)}</b>\n\n"
        "🌸 <i>اقلام خریداری‌شده به عنوان خریدهای انجام‌شده علامت خوردند. دست خریدار پر برکت!</i> ❤️"
    )
    sent = await message.answer(
        receipt_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 اطلاع‌رسانی خرید به اعضای گروه", callback_data=f"shop:bnotif:{exp_id}:{group_id}")],
            [InlineKeyboardButton(text="🛒 مشاهده لیست خریدهای خونه", callback_data=f"shop:view:{group_id}")],
            [InlineKeyboardButton(text="📊 وضعیت حساب‌ها و تراز مالی", callback_data=f"grp:report:{group_id}")],
            [InlineKeyboardButton(text="🏠 بازگشت به منوی دورهمی", callback_data=f"grp:view:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)


@router.callback_query(F.data.startswith("shop:bnotif:"))
async def handle_shopping_buy_notify(callback: CallbackQuery):
    parts = callback.data.split(":")
    exp_id = int(parts[2])
    group_id = int(parts[3])

    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    expense = await db.get_expense_by_id(exp_id, group_id)
    members = await db.get_group_members(group_id)
    buyer_id = callback.from_user.id
    buyer = next((m for m in members if m["id"] == buyer_id), None)
    buyer_name = (buyer.get("display_name") or buyer.get("nickname") or buyer.get("calling_name") or buyer["full_name"]) if buyer else "هم‌گروهی"

    # دریافت اقلام خریداری شده اخیر توسط این کاربر
    bought_items = await db.get_bought_shopping_items(group_id, limit=15)
    bought_by_user = [it for it in bought_items if it.get("buyer_id") == buyer_id]

    if bought_by_user:
        items_lines = "\n".join(f"• <b>{safe(it['item_name'])}</b> ({format_quantity(it['quantity'])})" for it in bought_by_user[:10])
    elif expense:
        items_lines = f"• <b>{safe(expense['title'])}</b>"
    else:
        items_lines = "• اقلام ثبت‌شده در فاکتور خرید اخیر"

    amount_str = format_amount(expense["amount"]) if expense else ""
    amount_line = f"\n💰 <b>مجموع کل فاکتور: {amount_str}</b>\n<i>(دنگ آن در حساب گروه محاسبه و ثبت شد)</i>\n" if amount_str else ""

    notice_text = (
        f"🛍️ <b>خریدهای خونه انجام شد!</b> 🧺✨\n\n"
        f"گروه: <b>«{safe(group['title'])}»</b>\n"
        f"👤 <b>خریدار:</b> {safe(buyer_name)}\n\n"
        f"✅ <b>اقلام زیر خریداری شدند و دیگر نیازی به خرید ندارند:</b>\n"
        f"{items_lines}\n"
        f"{amount_line}\n"
        f"🌸 <i>دست خریدار پر برکت و دلش شاد!</i> ❤️"
    )

    sent_count = 0
    for m in members:
        if m["id"] != buyer_id:
            try:
                await callback.bot.send_message(m["id"], notice_text, parse_mode="HTML")
                sent_count += 1
            except Exception:
                pass

    if sent_count > 0:
        await callback.answer(f"📢 خرید این اقلام با موفقیت به {sent_count} نفر از اعضای گروه اطلاع‌رسانی شد! 🌸", show_alert=True)
    else:
        await callback.answer("📢 پیام اطلاع‌رسانی آماده شد (هنوز عضو دیگری در گروه ثبت‌نام نکرده است).", show_alert=True)

    updated_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ به اعضای گروه اطلاع‌رسانی شد", callback_data="shop:bnotif_done")],
        [InlineKeyboardButton(text="🛒 مشاهده لیست خریدهای خونه", callback_data=f"shop:view:{group_id}")],
        [InlineKeyboardButton(text="📊 وضعیت حساب‌ها و تراز مالی", callback_data=f"grp:report:{group_id}")],
        [InlineKeyboardButton(text="🏠 بازگشت به منوی دورهمی", callback_data=f"grp:view:{group_id}")]
    ])
    try:
        await callback.message.edit_reply_markup(reply_markup=updated_markup)
    except Exception:
        pass


@router.callback_query(F.data == "shop:bnotif_done")
async def handle_shopping_buy_notify_done(callback: CallbackQuery):
    await callback.answer("این خرید قبلاً به اعضای گروه اطلاع‌رسانی شده است جان دلم! 🌸", show_alert=True)



# ===========================================================================
# فرآیند ویرایش اقلام لیست خرید (نام، تعداد، قیمت)
# ===========================================================================

@router.callback_query(F.data.startswith("shop:ed_menu:"))
async def handle_shopping_edit_menu(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    items = await db.get_group_shopping_items(group_id)
    if not items:
        await callback.answer("⚠️ لیست خرید خالی است!", show_alert=True)
        return

    await callback.answer()
    text = "✏️ <b>ویرایش اقلام لیست خریدهای خونه:</b>\n\nروی هر موردی که می‌خوای ویرایشش کنی بزن جان دلم:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.shopping_edit_items_keyboard(items, group_id))


@router.callback_query(F.data.startswith("shop:ed_it:"))
async def handle_shopping_edit_item_select(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    item_id = int(parts[2])
    group_id = int(parts[3])

    item = await db.get_shopping_item_by_id(item_id, group_id)
    if not item:
        await callback.answer("⚠️ این قلم یافت نشد!", show_alert=True)
        await handle_shopping_view(callback)
        return

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    tot_price = item.get("total_price", 0)
    price_info = format_amount(tot_price) if tot_price > 0 else "بدون قیمت (تعیین موقع خرید)"
    qty_info = format_quantity(item.get("quantity", 1))

    text = (
        f"✏️ <b>ویرایش قلم «{safe(item['item_name'])}»</b>\n\n"
        f"• عنوان فعلی: <b>{safe(item['item_name'])}</b>\n"
        f"• مقدار یا تعداد فعلی: <b>{qty_info}</b>\n"
        f"• وضعیت قیمت فعلی: <b>{price_info}</b>\n\n"
        f"چه بخشی از این قلم رو می‌خوای تغییر بدی {safe(calling_name)} قشنگم؟"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.shopping_edit_options_keyboard(item_id, group_id)
    )


@router.callback_query(F.data.startswith("shop:ed_fld:"))
async def handle_shopping_edit_field_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":")
    item_id = int(parts[2])
    group_id = int(parts[3])
    field = parts[4]

    item = await db.get_shopping_item_by_id(item_id, group_id)
    if not item:
        await callback.answer("⚠️ قلم یافت نشد!", show_alert=True)
        return

    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    await state.clear()
    await state.set_state(ShoppingItemStates.waiting_for_edit_input)
    await state.update_data(item_id=item_id, group_id=group_id, edit_field=field)

    if field == "name":
        prompt = (
            f"🏷️ <b>ویرایش نام کالا</b>\n\n"
            f"نام فعلی: <b>{safe(item['item_name'])}</b>\n\n"
            f"لطفاً <b>نام یا عنوان جدید</b> را بفرست {safe(calling_name)} جانم:\n"
            "<i>(مثلاً: <code>شیر کم چرب کاله</code>)</i>"
        )
    elif field == "qty":
        prompt = (
            f"🔢 <b>ویرایش مقدار یا تعداد</b>\n\n"
            f"مقدار فعلی قلم «{safe(item['item_name'])}»: <b>{format_quantity(item['quantity'])}</b>\n\n"
            f"لطفاً <b>تعداد یا مقدار جدید</b> را بفرست {safe(calling_name)} قشنگم:\n"
            "<i>(مثلاً: <code>4</code> یا <code>2.5</code>)</i>"
        )
    else:  # price
        curr_p = item.get("unit_price", 0)
        p_str = format_amount(curr_p) if curr_p > 0 else "تعیین نشده"
        prompt = (
            f"💵 <b>ویرایش یا ثبت قیمت واحد</b>\n\n"
            f"قیمت فعلی قلم «{safe(item['item_name'])}»: <b>{p_str}</b>\n\n"
            f"لطفاً <b>قیمت واحد جدید به تومان</b> را بفرست {safe(calling_name)} جانم:\n"
            "<i>(مثلاً: <code>45000</code> یا <code>۴۵ هزار</code>)</i>"
        )

    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف", callback_data=f"shop:ed_it:{item_id}:{group_id}")]
    ])
    await callback.message.edit_text(prompt, parse_mode="HTML", reply_markup=markup)


@router.message(ShoppingItemStates.waiting_for_edit_input)
async def handle_shopping_edit_input_submit(message: Message, state: FSMContext):
    user_id = message.from_user.id
    calling_name = await db.get_user_calling_name(user_id) or "جان دلم"
    data = await state.get_data()
    item_id = data.get("item_id")
    group_id = data.get("group_id")
    field = data.get("edit_field")

    raw_text = (message.text or "").strip()
    if not raw_text:
        return

    success_msg = ""
    if field == "name":
        if len(raw_text) > 80:
            sent = await message.answer("⚠️ نام کالا حداکثر ۸۰ کاراکتر باشد:")
            await db.record_chat_message(user_id, sent.message_id)
            return
        await db.update_shopping_item(item_id, group_id, item_name=raw_text)
        success_msg = f"✅ نام قلم با موفقیت به <b>«{safe(raw_text)}»</b> تغییر یافت {safe(calling_name)} جانم! 🌸"

    elif field == "qty":
        qty = parse_quantity(raw_text)
        if not qty or qty <= 0:
            sent = await message.answer("⚠️ لطفاً عددی مانند <code>4</code> یا <code>2.5</code> بفرست:")
            await db.record_chat_message(user_id, sent.message_id)
            return
        await db.update_shopping_item(item_id, group_id, quantity=qty)
        success_msg = f"✅ مقدار قلم با موفقیت به <b>{format_quantity(qty)}</b> تغییر یافت {safe(calling_name)} قشنگم! 🌸"

    elif field == "price":
        price = clean_amount_input(raw_text)
        if not price or price <= 0:
            sent = await message.answer("⚠️ لطفاً مبلغ معتبری به تومان بفرست (مثلاً: <code>45000</code>):")
            await db.record_chat_message(user_id, sent.message_id)
            return
        await db.update_shopping_item(item_id, group_id, unit_price=price)
        success_msg = f"✅ قیمت قلم با موفقیت به <b>{format_amount(price)}</b> به‌روزرسانی شد {safe(calling_name)} جانم! 🌸"

    await state.clear()
    await db.cleanup_chat_history(message.bot, user_id)
    try:
        await message.delete()
    except Exception:
        pass

    sent = await message.answer(
        success_msg,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 مشاهده لیست خریدهای خونه", callback_data=f"shop:view:{group_id}")],
            [InlineKeyboardButton(text="✏️ ویرایش قلم دیگر", callback_data=f"shop:ed_menu:{group_id}")]
        ])
    )
    await db.record_chat_message(user_id, sent.message_id)


# ===========================================================================
# سایر عملیات‌های لیست خرید: حذف قلم، خالی کردن، ثبت یکجا
# ===========================================================================

@router.callback_query(F.data.startswith("shop:del_menu:"))
async def handle_shopping_del_menu(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    items = await db.get_group_shopping_items(group_id)
    if not items:
        await callback.answer("لیست خرید خالی است!", show_alert=True)
        return

    await callback.answer()
    text = "🗑️ <b>حذف قلم از لیست خریدهای خونه:</b>\n\nروی هر قلمی که می‌خوای حذف بشه بزن عزیز دلم:"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.shopping_del_items_keyboard(items, group_id))


@router.callback_query(F.data.startswith("shop:del_do:"))
async def handle_shopping_del_do(callback: CallbackQuery):
    parts = callback.data.split(":")
    item_id = int(parts[2])
    group_id = int(parts[3])

    await db.delete_shopping_item(item_id, group_id)
    await callback.answer("✅ این قلم با موفقیت حذف شد جان دلم.", show_alert=True)
    await handle_shopping_view(callback)


@router.callback_query(F.data.startswith("shop:clear_confirm:"))
async def handle_shopping_clear_confirm(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    text = (
        "⚠️ <b>خالی کردن کل لیست خرید</b>\n\n"
        "کاملاً مطمئنی که می‌خوای تمام اقلام لیست خریدهای خونه پاک بشن عزیز دلم؟ ☕💔"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.shopping_clear_confirm_keyboard(group_id))


@router.callback_query(F.data.startswith("shop:clear_do:"))
async def handle_shopping_clear_do(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    await db.clear_group_shopping_items(group_id)
    await callback.answer("🧹 تمام اقلام لیست خرید پاک شدند جان دلم.", show_alert=True)
    await handle_shopping_view(callback)


@router.callback_query(F.data.startswith("shop:to_exp:"))
async def handle_shopping_to_expense(callback: CallbackQuery, state: FSMContext):
    group_id = int(callback.data.split(":")[2])
    items = await db.get_group_shopping_items(group_id)
    if not items:
        await callback.answer("⚠️ هنوز هیچ قلم خریدی برای ثبت وجود ندارد!", show_alert=True)
        return

    await callback.answer()
    total_amount = sum(it.get("total_price", 0) for it in items)
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
