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
        name = s["user"]["full_name"]
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
    
    calc_res = calculate_group_balances(members, active_expenses)
    settlements = calc_res["settlements"]
    
    if not settlements:
        text = (
            f"⚖️ <b>فرمول تسویه حساب گروه «{group['title']}»:</b>\n\n"
            "🎉 <b>همه حساب‌ها صاف است!</b>\n"
            "هیچ بدهی ثبت شده‌ای وجود ندارد و کسی به فرد دیگر بدهکار نیست."
        )
    else:
        lines = [
            f"⚖️ <b>فرمول تسویه حساب نهایی گروه «{group['title']}»</b>\n",
            "💡 <i>با انجام تراکنش‌های زیر (کمترین تعداد جابجایی پول)، تمام حساب‌ها کاملاً صاف و تسویه می‌شوند:</i>\n"
        ]
        
        for idx, item in enumerate(settlements, 1):
            payer_name = item["from_user"]["full_name"]
            receiver_name = item["to_user"]["full_name"]
            amt = format_amount(item["amount"])
            lines.append(f"{idx}️⃣ <b>{payer_name}</b> ➡️ باید <b>{amt}</b> به <b>{receiver_name}</b> بدهد.")
            
        lines.append("\n✅ <i>پس از انجام این واریزی‌ها، دکمه «صفر کردن حساب‌ها» را بزنید تا دوره بسته شود.</i>")
        text = "\n".join(lines)
        
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 مشاهده گزارش تفکیکی", callback_data=f"grp:report:{group_id}")],
        [InlineKeyboardButton(text="🔄 صفر کردن حساب‌ها", callback_data=f"grp:zero_confirm:{group_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


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
