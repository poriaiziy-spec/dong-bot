from helpers import format_amount

# فرهنگ لغات و شیوه‌های مکالمه اختصاصی ربات در ۳ لحن مختلف

TONE_NAMES = {
    "formal": "👔 رسمی و اداری",
    "friendly": "😊 دوستانه و محاوره",
    "toxic": "🔞 بی‌ادب و خفن (+18)"
}

def render_reminder_msg(tone: str, creditor_name: str, debtor_name: str, amount: int, card_info: str) -> str:
    """پیام یادآوری واریز دنگ به بدهکار"""
    amt_str = format_amount(amount)
    
    if tone == "formal":
        return (
            f"🔔 <b>یادآوری تسویه حساب مالی</b>\n\n"
            f"کاربر گرامی <b>{debtor_name}</b> با سلام،\n"
            f"احتراماً به اطلاع می‌رساند سهم بدهی شما به <b>{creditor_name}</b> به مبلغ <b>{amt_str}</b> هنوز تسویه نشده است.\n\n"
            f"💳 <b>اطلاعات حساب واریز:</b>\n{card_info}\n\n"
            f"خواهشمند است در اسرع وقت نسبت به واریز وجه و تسویه اقدام فرمایید. با تشکر."
        )
    elif tone == "toxic":
        return (
            f"🚨 <b>هوی الو! دنگتو صاف کن دیوث!</b>\n\n"
            f"آهای <b>{debtor_name}</b>! گدا بازی درنیار، <b>{creditor_name}</b> پیگیره که <b>{amt_str}</b> پول دنگتو هنوز نمالیدی به حسابش!\n\n"
            f"💳 <b>شماره کارتش اینه، بدو بریز تا فحش کش نشدی:</b>\n{card_info}\n\n"
            f"دست به جیب شو کون‌گشاد، مفت‌خوری موقوف! 🖕"
        )
    else:  # friendly
        return (
            f"🔔 <b>داداش یادآوری دنگ!</b>\n\n"
            f"سلام <b>{debtor_name}</b> گل! رفیقمون <b>{creditor_name}</b> یادآوری فرستاده که مبلغ <b>{amt_str}</b> از دنگت باقی مونده.\n\n"
            f"💳 <b>شماره کارتش اینه:</b>\n{card_info}\n\n"
            f"دمت گرم، هر وقت تونستی واریز کن حساب‌ها صاف شه 🌺"
        )

def render_payment_notice(tone: str, debtor_name: str, creditor_name: str, amount: int) -> str:
    """پیام اعلام واریز وجه توسط بدهکار به طلبکار"""
    amt_str = format_amount(amount)
    
    if tone == "formal":
        return (
            f"📩 <b>اعلام واریز وجه</b>\n\n"
            f"کاربر گرامی <b>{creditor_name}</b>،\n"
            f"هم‌اکنون <b>{debtor_name}</b> اعلام نمود که مبلغ <b>{amt_str}</b> را به حساب شما واریز کرده است.\n\n"
            f"لطفاً حساب بانکی خود را بررسی و در صورت صحت، تایید فرمایید."
        )
    elif tone == "toxic":
        return (
            f"🎉 <b>مژده بده! بالاخره دست به جیب شد!</b>\n\n"
            f"هوی <b>{creditor_name}</b>! این پفیوز <b>{debtor_name}</b> اعلام کرد که <b>{amt_str}</b> ریخته به حسابت!\n\n"
            f"حسابت رو چک کن ببین راست میگه یا چاخان کرده پولتو بالا کشیده! 👀"
        )
    else:  # friendly
        return (
            f"💸 <b>اعلام واریزی دنگ!</b>\n\n"
            f"سلام <b>{creditor_name}</b> جان،\n"
            f"<b>{debtor_name}</b> اعلام کرد که مبلغ <b>{amt_str}</b> رو برات واریز کرده.\n\n"
            f"یه سر به حسابت بزن ببین اوکیه یا نه رفیق ✨"
        )

def render_settlement_title(tone: str, group_title: str) -> str:
    """عنوان فرمول تسویه حساب"""
    if tone == "formal":
        return f"⚖️ <b>صورت‌حساب نهایی و دستورالعمل تسویه گروه «{group_title}»</b>\n"
    elif tone == "toxic":
        return f"⚖️ <b>فرمول حساب‌کشی و صاف کردن بدهی‌های «{group_title}»</b> 🔞\n"
    else:
        return f"⚖️ <b>فرمول تسویه حساب رفاقتی گروه «{group_title}»</b>\n"
