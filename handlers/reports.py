from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
import keyboards as kb
from calculator import calculate_group_balances
from helpers import format_amount, safe
from tones import (
    render_reminder_msg,
    render_payment_notice,
    render_settlement_title,
    render_no_expenses_msg,
    render_all_settled_msg,
    msg_zero_confirm,
    msg_zero_done
)

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
    group_tone = await db.get_group_tone(group_id)
    
    if not active_expenses:
        text = render_no_expenses_msg(group_tone, group["title"])
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💸 ثبت هزینه جدید", callback_data=f"exp:add:{group_id}")],
            [InlineKeyboardButton(text="🔙 بازگشت به بخش تسویه", callback_data=f"grp:sec_settle:{group_id}")]
        ])
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
        return

    calc_res = calculate_group_balances(members, active_expenses)
    total_spent = calc_res["total_spent"]
    stats = calc_res["member_stats"]
    
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"
    lines = [
        f"📊 <b>گزارش کامل حساب‌های دورهمی «{safe(group['title'])}»، {safe(calling_name)} قشنگم ☕❤️</b>\n",
        f"💰 کل هزینه‌های این دوره: <b>{format_amount(total_spent)}</b>",
        f"🧾 تعداد فاکتورها: <b>{len(active_expenses)}</b> مورد\n",
        "👥 <b>وضعیت حساب تک‌تک بچه‌ها:</b>"
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
        
    lines.append("👇 برای دیدن فرمول دقیق تسویه و حساب‌کتاب، دکمه زیر رو بزن عزیز دلم:")
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚖️ فرمول نهایی تسویه حساب", callback_data=f"grp:settle_calc:{group_id}")],
        [InlineKeyboardButton(text="🔄 صفر کردن حساب‌ها", callback_data=f"grp:zero_confirm:{group_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به بخش تسویه", callback_data=f"grp:sec_settle:{group_id}")]
    ])
    
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=markup)


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
        text = render_all_settled_msg(group_tone, group["title"])
    else:
        lines = [
            f"{render_settlement_title(group_tone, group['title'])}",
            "💡 <i>تراکنش‌های بهینه جهت صاف شدن کامل حساب‌ها با کمترین تعداد جابجایی:</i>\n"
        ]
        
        for idx, item in enumerate(settlements, 1):
            debtor = item["from_user"]
            creditor = item["to_user"]
            debtor_name = safe(debtor.get("display_name", debtor["full_name"]))
            creditor_name = safe(creditor.get("display_name", creditor["full_name"]))
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
            
            c_label = creditor.get("display_name") or creditor.get("nickname") or creditor["full_name"]
            d_label = debtor.get("display_name") or debtor.get("nickname") or debtor["full_name"]
            # افزودن دکمه‌های اقدام سریع
            markup_buttons.append([
                InlineKeyboardButton(
                    text=f"💸 اعلام واریز به {c_label}",
                    callback_data=f"pay:notify:{group_id}:{debtor['id']}:{creditor['id']}:{item['amount']}"
                ),
                InlineKeyboardButton(
                    text="✅ تسویه این بدهی",
                    callback_data=f"pay:dir:{group_id}:{debtor['id']}:{creditor['id']}:{item['amount']}"
                )
            ])
            markup_buttons.append([
                InlineKeyboardButton(
                    text=f"🔔 یادآوری به {d_label}",
                    callback_data=f"pay:remind:{group_id}:{debtor['id']}:{creditor['id']}:{item['amount']}"
                )
            ])
            
        lines.append("✅ <i>هر واریزی که انجام شد، با تایید طلبکار یا با دکمه‌های زیر می‌توانید حساب هر فرد را جداگانه یا کل گروه را یکجا صفر کنید.</i>")
        text = "\n".join(lines)
        
    markup_buttons.append([
        InlineKeyboardButton(text="📋 متن آماده کپی/فوروارد به گروه", callback_data=f"grp:share_summary:{group_id}")
    ])
    markup_buttons.append([
        InlineKeyboardButton(text="📊 مشاهده گزارش تفکیکی", callback_data=f"grp:report:{group_id}")
    ])
    markup_buttons.append([
        InlineKeyboardButton(text="👤 صفر کردن حساب یک فرد", callback_data=f"grp:zero_mem_menu:{group_id}"),
        InlineKeyboardButton(text="🔄 صفر کردن کلی گروه", callback_data=f"grp:zero_confirm:{group_id}")
    ])
    markup_buttons.append([
        InlineKeyboardButton(text="🔙 بازگشت به بخش تسویه", callback_data=f"grp:sec_settle:{group_id}")
    ])
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=markup_buttons))


@router.callback_query(F.data.startswith("grp:share_summary:"))
async def handle_share_summary(callback: CallbackQuery):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group:
        return
    members = await db.get_group_members(group_id)
    active_expenses = await db.get_active_expenses(group_id)
    if not active_expenses:
        await callback.answer("هنوز خرجی در این دوره ثبت نشده است!", show_alert=True)
        return
        
    calc_res = calculate_group_balances(members, active_expenses)
    total_spent = calc_res["total_spent"]
    settlements = calc_res["settlements"]
    
    lines = [
        f"📊 خلاصه حساب‌های گروه «{group['title']}»",
        f"💰 مجموع هزینه‌ها: {format_amount(total_spent)}",
        "─────────────────"
    ]
    if not settlements:
        lines.append("🎉 تمامی حساب‌ها تسویه و صاف است!")
    else:
        lines.append("⚖️ مبالغ پرداختی و تسویه نهایی:")
        for idx, item in enumerate(settlements, 1):
            d_name = item["from_user"].get("display_name") or item["from_user"].get("nickname") or item["from_user"].get("full_name", "کاربر")
            c_name = item["to_user"].get("display_name") or item["to_user"].get("nickname") or item["to_user"].get("full_name", "کاربر")
            card = item["to_user"].get("card_number")
            card_txt = f" (کارت: {format_card_number(card)})" if card else ""
            lines.append(f"{idx}. {d_name} ➔ {format_amount(item['amount'])} ➔ {c_name}{card_txt}")
    
    lines.append("─────────────────")
    lines.append("🤖 محاسبه شده با ربات کافه دنگ ☕")
    
    share_text = "\n".join(lines)
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "عزیز دلم"
    await callback.message.answer(
        f"📋 <b>متن آماده برای کپی یا فوروارد به گروه دوستان، {safe(calling_name)} جانم:</b>\n<i>(روی کادر زیر بزنی خودش کپی میشه قشنگم)</i>\n\n<code>{safe(share_text)}</code>",
        parse_mode="HTML"
    )


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
        
    c_name = creditor.get("display_name") or creditor.get("nickname") or creditor["full_name"]
    d_name = debtor.get("display_name") or debtor.get("nickname") or debtor["full_name"]
    reminder_text = render_reminder_msg(
        tone=group_tone,
        creditor_name=c_name,
        debtor_name=d_name,
        amount=amount,
        card_info=card_info
    )
    
    try:
        await callback.bot.send_message(debtor_id, reminder_text, parse_mode="HTML")
        await callback.answer(f"✅ پیام یادآوری با موفقیت برای {d_name} ارسال شد!", show_alert=True)
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
        
    c_name = creditor.get("display_name") or creditor.get("nickname") or creditor["full_name"]
    d_name = debtor.get("display_name") or debtor.get("nickname") or debtor["full_name"]
    notice_text = render_payment_notice(
        tone=group_tone,
        debtor_name=d_name,
        creditor_name=c_name,
        amount=amount
    )
    
    confirm_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تایید دریافت وجه", callback_data=f"pay:ack:{group_id}:{debtor_id}:{creditor_id}:{amount}"),
            InlineKeyboardButton(text="❌ هنوز نیامده", callback_data=f"pay:nack:{group_id}:{debtor_id}:{creditor_id}")
        ]
    ])
    
    try:
        await callback.bot.send_message(creditor_id, notice_text, parse_mode="HTML", reply_markup=confirm_markup)
        await callback.answer(f"✅ پیام اعلام واریزی برای {c_name} ارسال شد!", show_alert=True)
    except Exception as e:
        await callback.answer("⚠️ خطا در ارسال پیام به طلبکار (باید ربات را استارت کرده باشد).", show_alert=True)


async def _find_group_for_debt(debtor_id: int, creditor_id: int) -> int | None:
    """یافتن گروه مشترکی که این دو عضو در آن حضور دارند"""
    user_groups = await db.get_user_groups(debtor_id)
    for g in user_groups:
        gid = g["id"]
        members = await db.get_group_members(gid)
        if any(m["id"] == creditor_id for m in members):
            return gid
    return None


@router.callback_query(F.data.startswith("pay:ack:"))
async def handle_ack_payment(callback: CallbackQuery):
    parts = callback.data.split(":")
    if len(parts) >= 6:
        group_id = int(parts[2])
        debtor_id = int(parts[3])
        creditor_id = int(parts[4])
        amount = int(parts[5])
    else:
        debtor_id = int(parts[2])
        creditor_id = int(parts[3])
        amount = int(parts[4])
        group_id = await _find_group_for_debt(debtor_id, creditor_id)

    # صفر کردن رسمی بدهی در دیتابیس
    if group_id:
        await db.record_debt_settlement(group_id, debtor_id, creditor_id, amount)

    await callback.answer("✅ دریافت وجه تایید و این بدهی در سیستم کاملاً صفر شد!", show_alert=True)
    base_text = safe(callback.message.text or "")
    await callback.message.edit_text(
        base_text + f"\n\n🟢 <b>وضعیت: توسط طلبکار تایید شد و مبلغ {format_amount(amount)} با موفقیت تسویه و در حساب‌های گروه صفر گردید.</b>",
        parse_mode="HTML"
    )
    
    try:
        debtor_calling = await db.get_user_calling_name(debtor_id) or "عزیز دلم"
        await callback.bot.send_message(
            debtor_id,
            f"🎉 <b>واریزی شما تایید شد {safe(debtor_calling)} قشنگم!</b>\nطلبکار دریافت مبلغ <b>{format_amount(amount)}</b> رو تایید کرد و این بدهی در گروه کاملاً <b>صفر و تسویه</b> شد. دستت طلا و دمت گرم! ☕❤️",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("pay:nack:"))
async def handle_nack_payment(callback: CallbackQuery):
    parts = callback.data.split(":")
    debtor_id = int(parts[3]) if len(parts) >= 5 else int(parts[2])
    await callback.answer("پیام عدم دریافت ثبت شد.")
    base_text = safe(callback.message.text or "")
    await callback.message.edit_text(base_text + "\n\n🔴 <b>وضعیت: طلبکار اعلام کرد پولی دریافت نشده است!</b>", parse_mode="HTML")
    
    try:
        debtor_calling = await db.get_user_calling_name(debtor_id) or "جان دلم"
        await callback.bot.send_message(
            debtor_id,
            f"⚠️ <b>{safe(debtor_calling)} جانم:</b> طلبکار اعلام کرد که هنوز واریزی از طرفت براش ننشسته. بی زحمت فیش یا حسابت رو چک بکن فدات شم. ☕",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("pay:dir:"))
async def handle_direct_settle_debt(callback: CallbackQuery):
    """تسویه مستقیم و بدون معطلی یک بدهی توسط طلبکار یا سرگروه"""
    parts = callback.data.split(":")
    group_id = int(parts[2])
    debtor_id = int(parts[3])
    creditor_id = int(parts[4])
    amount = int(parts[5])

    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    # فقط طلبکار یا سرگروه مجاز به تایید تسویه این بدهی هستند
    if callback.from_user.id != creditor_id and callback.from_user.id != group["created_by"]:
        await callback.answer("⚠️ فقط طلبکار یا سرگروه می‌توانند تسویه این بدهی را ثبت کنند.", show_alert=True)
        return

    await db.record_debt_settlement(group_id, debtor_id, creditor_id, amount)
    await callback.answer("✅ این بدهی با موفقیت تسویه و در حساب‌ها صفر شد!", show_alert=True)
    await handle_group_balances(callback)


@router.callback_query(F.data.startswith("grp:zero_mem_menu:"))
async def handle_zero_member_menu(callback: CallbackQuery):
    """منوی انتخاب عضو جهت صفر کردن حساب جداگانه"""
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    members = await db.get_group_members(group_id)
    active_expenses = await db.get_active_expenses(group_id)
    calc_res = calculate_group_balances(members, active_expenses)
    stats = calc_res["member_stats"]

    # فیلتر اعضایی که تراز غیر صفر دارند (بدهکار یا طلبکار)
    active_members = [s for s in stats if abs(s["net"]) > 0.5]
    if not active_members:
        await callback.answer("✨ تمام حساب‌ها در این گروه در حال حاضر صاف و صفر هستند!", show_alert=True)
        return

    await callback.answer()
    lines = [
        f"👤 <b>صفر کردن حساب جداگانه افراد در «{safe(group['title'])}»:</b>\n",
        "عزیز دلم، فردی که می‌خواهی حساب و دنگ‌هایش در این دوره کاملاً صاف و صفر شود را انتخاب کن:"
    ]
    buttons = []
    for s in active_members:
        u = s["user"]
        u_name = u.get("display_name") or u.get("nickname") or u.get("calling_name") or u.get("full_name") or "عضو"
        net = s["net"]
        if net < 0:
            status_text = f"🔴 {u_name} (بدهکار: {format_amount(abs(net))})"
        else:
            status_text = f"🟢 {u_name} (طلبکار: {format_amount(net)})"
        buttons.append([InlineKeyboardButton(text=status_text, callback_data=f"grp:zero_mem_ask:{group_id}:{u['id']}")])

    buttons.append([InlineKeyboardButton(text="🔙 بازگشت به تسویه", callback_data=f"grp:sec_settle:{group_id}")])
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("grp:zero_mem_ask:"))
async def handle_zero_member_ask(callback: CallbackQuery):
    """تاییدیه صفر کردن حساب یک فرد مشخص"""
    parts = callback.data.split(":")
    group_id = int(parts[2])
    target_id = int(parts[3])

    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    target_name = await db.get_user_calling_name(target_id) or "این عضو"
    text = (
        f"⚠️ <b>تایید صفر کردن حساب جداگانه «{safe(target_name)}»:</b>\n\n"
        f"آیا مطمئن هستید که می‌خواهید تمام حساب‌ها، بدهی‌ها و طلب‌های <b>{safe(target_name)}</b> در دورهمی «{safe(group['title'])}» صفر و تسویه شوند؟\n\n"
        f"💡 <i>با این کار، حساب بقیه افراد بدون تغییر باقی مانده و فقط حساب {safe(target_name)} تسویه خواهد شد.</i>"
    )
    buttons = [
        [
            InlineKeyboardButton(text="✅ بله، حسابش صفر شود", callback_data=f"grp:zero_mem_do:{group_id}:{target_id}"),
            InlineKeyboardButton(text="❌ انصراف", callback_data=f"grp:zero_mem_menu:{group_id}")
        ]
    ]
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("grp:zero_mem_do:"))
async def handle_zero_member_do(callback: CallbackQuery):
    """اجرای صفر کردن حساب فرد مشخص"""
    parts = callback.data.split(":")
    group_id = int(parts[2])
    target_id = int(parts[3])

    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    if callback.from_user.id != group["created_by"] and callback.from_user.id != target_id:
        await callback.answer("⚠️ فقط سرگروه یا خود عضو مجاز به تایید صفر کردن حساب هستند.", show_alert=True)
        return

    count = await db.settle_member_balance(group_id, target_id)
    target_name = await db.get_user_calling_name(target_id) or "این عضو"
    await callback.answer("✅ حساب با موفقیت صفر و تسویه شد!", show_alert=True)

    text = (
        f"🎉 <b>حساب «{safe(target_name)}» با موفقیت صفر شد!</b> ☕❤️\n\n"
        f"تمام بدهی‌ها و دنگ‌های مربوط به {safe(target_name)} در دورهمی «{safe(group['title'])}» تسویه شد و تراز ایشان صفر گردید."
    )
    buttons = [
        [InlineKeyboardButton(text="📊 مشاهده تراز و تسویه گروه", callback_data=f"grp:sec_settle:{group_id}")],
        [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
    ]
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("grp:zero_confirm:"))
async def handle_zero_confirm(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    await callback.answer()
    is_creator = (group["created_by"] == callback.from_user.id)
    calling_name = await db.get_user_calling_name(callback.from_user.id) or "جان دلم"

    if is_creator:
        group_tone = await db.get_group_tone(group_id)
        text = msg_zero_confirm(group_tone, group["title"])
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=kb.zero_confirm_keyboard(group_id)
        )
    else:
        # اگر عضو عادی باشد، امکان ارسال درخواست به مدیر برای تایید نهایی فراهم است
        creator_calling = await db.get_user_calling_name(group["created_by"]) or "سرگروه"
        text = (
            f"🔄 <b>درخواست صفر کردن حساب‌های دورهمی «{safe(group['title'])}»، {safe(calling_name)} قشنگم:</b> ☕❤️\n\n"
            f"عزیز دلم، صفر کردن قطعی حساب‌ها و بستن دوره مالی نیاز به تایید نهایی سرگروه (<b>{safe(creator_calling)}</b>) دارد.\n\n"
            "با زدن دکمه زیر، یک درخواست برای سرگروه ارسال می‌شود تا پس از بررسی واریزی‌ها، تایید نهایی را صادر کند.\n\n"
            "آیا مایل به ارسال درخواست صفر کردن به سرگروه هستی؟"
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📩 ارسال درخواست به سرگروه جهت تایید", callback_data=f"grp:zero_req:{group_id}")],
            [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data.startswith("grp:zero_req:"))
async def handle_zero_request_send(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    member_id = callback.from_user.id
    member_calling = await db.get_user_calling_name(member_id) or callback.from_user.full_name
    creator_id = group["created_by"]
    creator_calling = await db.get_user_calling_name(creator_id) or "جان دلم"

    req_text = (
        f"🔔 <b>درخواست صفر کردن حساب‌های دورهمی «{safe(group['title'])}»</b> ☕\n\n"
        f"عضو گروه، <b>{safe(member_calling)}</b>، درخواست داده است که حساب‌های دوره جاری تسویه و صفر شوند.\n\n"
        f"آیا تمام واریزی‌ها انجام شده و تایید می‌کنی که حساب‌ها صفر شوند {safe(creator_calling)} جانم؟"
    )
    req_markup = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ تایید و صفر کردن حساب‌ها", callback_data=f"grp:zero_appr:{group_id}:{member_id}"),
            InlineKeyboardButton(text="❌ رد درخواست", callback_data=f"grp:zero_rej:{group_id}:{member_id}")
        ]
    ])

    try:
        await callback.bot.send_message(creator_id, req_text, parse_mode="HTML", reply_markup=req_markup)
        await callback.answer("✅ درخواست صفر کردن با موفقیت برای سرگروه ارسال شد!", show_alert=True)

        member_text = (
            f"✅ <b>درخواست صفر کردن حساب‌ها برای سرگروه ارسال شد {safe(member_calling)} قشنگم!</b> ☕❤️\n\n"
            "پیام تایید برای سرگروه فرستاده شد. به محض اینکه ایشان تایید نهایی را بزنند، حساب‌ها به صورت خودکار صفر شده و به شما هم اطلاع می‌دهم."
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
        await callback.message.edit_text(member_text, parse_mode="HTML", reply_markup=markup)
    except Exception:
        await callback.answer("⚠️ خطا در ارسال پیام به سرگروه (سرگروه باید ربات را استارت داشته باشد).", show_alert=True)


@router.callback_query(F.data.startswith("grp:zero_appr:"))
async def handle_zero_approve(callback: CallbackQuery):
    parts = callback.data.split(":")
    group_id = int(parts[2])
    member_id = int(parts[3])

    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    if group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ فقط سرگروه مجاز به تایید نهایی است!", show_alert=True)
        return

    settled_count = await db.settle_group(group_id)
    group_tone = await db.get_group_tone(group_id)
    await callback.answer("✅ دوره مالی با تایید شما بسته و حساب‌ها صفر شدند!", show_alert=True)

    done_msg = msg_zero_done(group_tone, group["title"], settled_count)
    await callback.message.edit_text(
        f"{done_msg}\n\n🟢 <b>وضعیت: توسط سرگروه تایید و نهایی شد.</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    )

    try:
        member_calling = await db.get_user_calling_name(member_id) or "عزیز دلم"
        await callback.bot.send_message(
            member_id,
            f"🎉 <b>درخواست صفر کردن حساب‌های دورهمی «{safe(group['title'])}» توسط سرگروه تایید شد!</b> ☕❤️✨\n\n"
            f"تمام حساب‌ها و دنگ‌ها با موفقیت صاف و صفر شدند {safe(member_calling)} قشنگم.",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("grp:zero_rej:"))
async def handle_zero_reject(callback: CallbackQuery):
    parts = callback.data.split(":")
    group_id = int(parts[2])
    member_id = int(parts[3])

    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    if group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ فقط سرگروه مجاز به مدیریت این درخواست است!", show_alert=True)
        return

    await callback.answer("درخواست صفر کردن حساب‌ها رد شد.")
    base_text = safe(callback.message.text or "")
    await callback.message.edit_text(
        base_text + "\n\n🔴 <b>وضعیت: توسط سرگروه رد شد (واریزی‌ها هنوز کامل نشده است).</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
        ])
    )

    try:
        member_calling = await db.get_user_calling_name(member_id) or "جان دلم"
        await callback.bot.send_message(
            member_id,
            f"ℹ️ <b>{safe(member_calling)} جانم:</b> سرگروه در حال حاضر درخواست صفر کردن حساب‌های دورهمی «{safe(group['title'])}» را رد کرد؛ احتمالاً هنوز برخی واریزی‌ها یا حساب‌کتاب‌ها صاف نشده است. لطفاً با سرگروه هماهنگ کنید ☕",
            parse_mode="HTML"
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("grp:zero_do:"))
async def handle_zero_execute(callback: CallbackQuery):
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    if group["created_by"] != callback.from_user.id:
        await callback.answer("⚠️ تایید نهایی فقط با سرگروه است عزیز دلم!", show_alert=True)
        return
        
    group_tone = await db.get_group_tone(group_id)
    settled_count = await db.settle_group(group_id)
    await callback.answer("✅ حساب‌ها با موفقیت صفر شدند جان دلم!", show_alert=True)
    
    text = msg_zero_done(group_tone, group["title"], settled_count)
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به گروه", callback_data=f"grp:view:{group_id}")]
    ])
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
