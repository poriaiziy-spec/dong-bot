from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
import keyboards as kb
from calculator import calculate_group_balances
from helpers import format_amount

router = Router()

@router.callback_query(F.data.startswith("grp:report:"))
async def handle_group_report(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return
        
    members = await db.get_group_members(group_id)
    active_expenses = await db.get_active_expenses(group_id)
    
    if not active_expenses:
        text = (
            f"📊 <b>گزارش حساب‌های گروه «{group['title']}»:</b>\n\n"
            "📭 در حال حاضر هیچ هزینه فعالی در این دوره ثبت نشده است یا حساب‌ها قبلاً صفر شده‌اند.\n\n"
            "برای شروع می‌توانید از منوی گروه گزینه «💸 ثبت هزینه جدید» را انتخاب کنید."
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 ثبت هزینه جدید", callback_data=f"exp:add:{group_id}")],
            [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        return

    calc_res = calculate_group_balances(members, active_expenses)
    total_spent = calc_res["total_spent"]
    stats = calc_res["member_stats"]
    
    lines = [
        f"📊 <b>گزارش کامل حساب‌های گروه «{group['title']}»</b>\n",
        f"💰 کل هزینه‌های دوره جاری: <b>{format_amount(total_spent)}</b>",
        f"🧾 تعداد فاکتورها: <b>{len(active_expenses)}</b> مورد\n",
        "👥 <b>وضعیت اعضا:</b>"
    ]
    
    for s in stats:
        name = s["user"].get("display_name", s["user"]["full_name"])
        paid = format_amount(s["paid"])
        owed = format_amount(s["owed"])
        net = s["net"]
        
        if net > 0:
            status_text = f"🟢 <b>{format_amount(net)} طلبکار</b>"
        elif net < 0:
            status_text = f"🔴 <b>{format_amount(-net)} بدهکار</b>"
        else:
            status_text = "⚪ <b>بی‌حساب (تسویه)</b>"
            
        lines.append(
            f"▫️ <b>{name}</b>:\n"
            f"   • پرداختی کل: {paid}\n"
            f"   • سهم دنگ: {owed}\n"
            f"   • وضعیت نهایی: {status_text}\n"
        )
        
    lines.append("👇 برای دیدن فرمول نهایی پرداخت و تسویه، دکمه زیر را بزنید:")
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚖️ فرمول نهایی تسویه حساب", callback_data=f"grp:settle_calc:{group_id}")],
        [InlineKeyboardButton(text="🔄 صفر کردن حساب‌ها", callback_data=f"grp:zero_confirm:{group_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
    ])
    
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=markup)


from tones import render_reminder_msg, render_payment_notice, render_settlement_title
from bank_utils import format_card_number

@router.callback_query(F.data.startswith("grp:settle_calc:"))
async def handle_settlement_calculation(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return
        
    members = await db.get_group_members(group_id)
    active_expenses = await db.get_active_expenses(group_id)
    group_tone = await db.get_group_tone(group_id)
    
    calc_res = calculate_group_balances(members, active_expenses)
    settlements = calc_res["settlements"]
    
    markup_buttons = []
    
    if not settlements:
        text = (
            f"{render_settlement_title(group_tone, group['title'])}\n"
            "🎉 <b>همه حساب‌ها صاف است!</b>\n"
            "هیچ بدهی ثبت شده‌ای وجود ندارد و کسی به دیگری بدهکار نیست."
        )
    else:
        lines = [
            f"{render_settlement_title(group_tone, group['title'])}",
            "💡 <i>تراکنش‌های بهینه جهت صاف شدن کامل حساب‌ها با کمترین تعداد جابجایی:</i>\n"
        ]
        
        for idx, item in enumerate(settlements, 1):
            debtor = item["from_user"]
            creditor = item["to_user"]
            debtor_name = debtor.get("display_name", debtor["full_name"])
            creditor_name = creditor.get("display_name", creditor["full_name"])
            amt = format_amount(item["amount"])
            
            card_num = creditor.get("card_number")
            bank_name = creditor.get("bank_name")
            
            if card_num:
                card_str = f"<code>{format_card_number(card_num)}</code> ({bank_name or 'بانک'})"
            else:
                card_str = "<i>(هنوز کارتی ثبت نکرده)</i>"
                
            lines.append(
                f"{idx}️⃣ <b>{debtor_name}</b> ➡️ باید <b>{amt}</b> به <b>{creditor_name}</b> بدهد.\n"
                f"   💳 شماره کارت: {card_str}\n"
            )
            
            # افزودن دکمه‌های اقدام سریع
            markup_buttons.append([
                InlineKeyboardButton(
                    text=f"💸 اعلام واریز به {creditor['full_name']}",
                    callback_data=f"pay:notify:{group_id}:{debtor['id']}:{creditor['id']}:{item['amount']}"
                ),
                InlineKeyboardButton(
                    text=f"🔔 یادآوری به {debtor['full_name']}",
                    callback_data=f"pay:remind:{group_id}:{debtor['id']}:{creditor['id']}:{item['amount']}"
                )
            ])
            
        lines.append("✅ <i>پس از انجام واریزی‌ها، دکمه «صفر کردن حساب‌ها» را بزنید تا دوره بسته شود.</i>")
        text = "\n".join(lines)
        
    markup_buttons.append([
        InlineKeyboardButton(text="📊 مشاهده گزارش تفکیکی", callback_data=f"grp:report:{group_id}")
    ])
    markup_buttons.append([
        InlineKeyboardButton(text="🔄 صفر کردن حساب‌ها", callback_data=f"grp:zero_confirm:{group_id}"),
        InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=markup_buttons))


@router.callback_query(F.data.startswith("pay:remind:"))
async def handle_payment_reminder(callback: CallbackQuery):
    parts = callback.data.split(":")
    group_id = int(parts[2])
    debtor_id = int(parts[3])
    creditor_id = int(parts[4])
    amount = int(parts[5])
    
    group = await db.get_group_by_id(group_id)
    members = await db.get_group_members(group_id)
    group_tone = await db.get_group_tone(group_id)
    
    debtor = next((m for m in members if m["id"] == debtor_id), None)
    creditor = next((m for m in members if m["id"] == creditor_id), None)
    
    if not debtor or not creditor:
        await callback.answer("کاربر یافت نشد!", show_alert=True)
        return
        
    card_num = creditor.get("card_number")
    bank_name = creditor.get("bank_name")
    if card_num:
        card_info = f"شماره کارت: <code>{format_card_number(card_num)}</code> ({bank_name or 'بانک'})"
    else:
        card_info = "شماره کارت ثبت نشده (لطفاً از طریق ربات ثبت کنید)"
        
    reminder_text = render_reminder_msg(
        tone=group_tone,
        creditor_name=creditor["full_name"],
        debtor_name=debtor["full_name"],
        amount=amount,
        card_info=card_info
    )
    
    try:
        await callback.bot.send_message(debtor_id, reminder_text, parse_mode="HTML")
        await callback.answer(f"✅ پیام یادآوری با موفقیت برای {debtor['full_name']} ارسال شد!", show_alert=True)
    except Exception as e:
        await callback.answer("⚠️ امکان ارسال پیام به کاربر وجود ندارد (کاربر باید ربات را استارت کرده باشد).", show_alert=True)


@router.callback_query(F.data.startswith("pay:notify:"))
async def handle_payment_notification(callback: CallbackQuery):
    parts = callback.data.split(":")
    group_id = int(parts[2])
    debtor_id = int(parts[3])
    creditor_id = int(parts[4])
    amount = int(parts[5])
    
    group = await db.get_group_by_id(group_id)
    members = await db.get_group_members(group_id)
    group_tone = await db.get_group_tone(group_id)
    
    debtor = next((m for m in members if m["id"] == debtor_id), None)
    creditor = next((m for m in members if m["id"] == creditor_id), None)
    
    if not debtor or not creditor:
        await callback.answer("کاربر یافت نشد!", show_alert=True)
        return
        
    notice_text = render_payment_notice(
        tone=group_tone,
        debtor_name=debtor["full_name"],
        creditor_name=creditor["full_name"],
        amount=amount
    )
    
    confirm_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تایید دریافت وجه", callback_data=f"pay:ack:{debtor_id}:{creditor_id}:{amount}"),
            InlineKeyboardButton(text="❌ هنوز نیامده", callback_data=f"pay:nack:{debtor_id}:{creditor_id}")
        ]
    ])
    
    try:
        await callback.bot.send_message(creditor_id, notice_text, parse_mode="HTML", reply_markup=confirm_markup)
        await callback.answer(f"✅ پیام اعلام واریزی برای {creditor['full_name']} ارسال شد!", show_alert=True)
    except Exception as e:
        await callback.answer("⚠️ خطا در ارسال پیام به طلبکار (باید ربات را استارت کرده باشد).", show_alert=True)


@router.callback_query(F.data.startswith("pay:ack:"))
async def handle_ack_payment(callback: CallbackQuery):
    parts = callback.data.split(":")
    debtor_id = int(parts[2])
    creditor_id = int(parts[3])
    amount = int(parts[4])
    
    await callback.answer("✅ دریافت وجه تایید شد!")
    await callback.message.edit_text(callback.message.text + "\n\n🟢 <b>وضعیت: توسط طلبکار تایید شد.</b>", parse_mode="HTML")
    
    try:
        await callback.bot.send_message(
            debtor_id,
            f"🎉 <b>واریزی شما تایید شد!</b>\nطلبکار دریافت مبلغ <b>{format_amount(amount)}</b> را تایید کرد. دمت گرم!",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("pay:nack:"))
async def handle_nack_payment(callback: CallbackQuery):
    debtor_id = int(callback.data.split(":")[2])
    await callback.answer("پیام عدم دریافت ثبت شد.")
    await callback.message.edit_text(callback.message.text + "\n\n🔴 <b>وضعیت: طلبکار اعلام کرد پولی دریافت نشده است!</b>", parse_mode="HTML")
    
    try:
        await callback.bot.send_message(
            debtor_id,
            "⚠️ <b>توجه:</b> طلبکار اعلام کرد که واریزی از طرف شما دریافت نکرده است. لطفاً فیش یا حسابتان را بررسی کنید.",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("grp:zero_confirm:"))
async def handle_zero_confirm(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    
    text = (
        f"⚠️ <b>تأییدیه صفر کردن و بستن دوره مالی گروه «{group['title']}»</b>\n\n"
        "آیا مطمئن هستید که می‌خواهید حساب‌ها را صفر کنید؟\n\n"
        "• با انجام این کار، تمام بدهی‌ها و هزینه‌های فعلی به وضعیت «تسویه شده» درمی‌آیند.\n"
        "• حساب تمام اعضا در دوره جدید صفر خواهد شد.\n"
        "• سوابق تمام خرج‌ها در بخش تاریخچه ذخیره خواهد ماند."
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.zero_confirm_keyboard(group_id)
    )


@router.callback_query(F.data.startswith("grp:zero_do:"))
async def handle_zero_execute(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    
    settled_count = await db.settle_group(group_id)
    await callback.answer("✅ حساب‌ها با موفقیت صفر شدند!", show_alert=True)
    
    text = (
        f"🎉 <b>حساب‌های گروه «{group['title']}» با موفقیت صفر و تسویه شدند!</b>\n\n"
        f"تعداد {settled_count} هزینه در این دوره بسته و بایگانی شدند.\n"
        "دوره مالی جدید از صفر شروع شد. خریدهای بعدی را می‌توانید مجدداً ثبت کنید."
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
