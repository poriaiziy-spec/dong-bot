import html
from helpers import format_amount

def _s(t): return html.escape(str(t)) if t else ""

TONE_NAMES = {
    "formal": "👔 رسمی و اداری",
    "friendly": "😊 دوستانه و خودمونی",
    "toxic": "🔞 بی‌ادب و خفن (+18)"
}

# ----------------- پیام‌های داشبورد گروه -----------------
def msg_group_dashboard(tone: str, title: str, member_count: int, member_lines: str, total_amount: int, expenses_count: int, tone_name: str) -> str:
    title = _s(title)
    amt_str = format_amount(total_amount)
    
    if tone == "formal":
        return (
            f"📁 <b>اطلاعات گروه: {title}</b>\n\n"
            f"👥 <b>فهرست اعضای محترم ({member_count} نفر):</b>\n{member_lines}\n\n"
            f"📊 <b>گردش مالی دوره جاری:</b> {amt_str}\n"
            f"🧾 <b>تعداد اقلام هزینه:</b> {expenses_count} فقره\n"
            f"🎭 <b>شیوه مکالمه سازمانی:</b> {tone_name}\n\n"
            "لطفاً جهت ثبت یا پیگیری امور مالی، یکی از گزینه‌های زیر را انتخاب فرمایید:"
        )
    elif tone == "toxic":
        return (
            f"📁 <b>گنگ و پاتوق: {title}</b>\n\n"
            f"👥 <b>لیست اوباش و لاشی‌های گروه ({member_count} نفر):</b>\n{member_lines}\n\n"
            f"💸 <b>کل پولی که به باد فنا دادید:</b> {amt_str}\n"
            f"🧾 <b>تعداد فاکتورهای کوفتی:</b> {expenses_count} تا\n"
            f"🎭 <b>لحن صحبت:</b> {tone_name}\n\n"
            "حالا کدوم گوری می‌خوای بری؟ دکمه‌ها رو بزن معطل نکن:"
        )
    else:  # friendly (خودمونی و محاوره)
        return (
            f"📁 <b>دورهمی: {title}</b> ☕\n\n"
            f"👥 <b>رفقای حاضر تو گروه ({member_count} نفر):</b>\n{member_lines}\n\n"
            f"💰 <b>تا الان چقدر پیاده شدیم:</b> {amt_str}\n"
            f"🧾 <b>تعداد خریدها و خرج‌ها:</b> {expenses_count} تا\n"
            f"🎭 <b>لحن گپ ربات:</b> {tone_name}\n\n"
            "خب رفیق، چه کاری می‌خوای انجام بدی؟ یکی رو انتخاب کن:"
        )

# ----------------- پیام‌های ثبت هزینه -----------------
def msg_expense_title_prompt(tone: str) -> str:
    if tone == "formal":
        return "📌 <b>عنوان هزینه:</b>\nلطفاً بابت/شرح فاکتور هزینه را مرقوم فرمایید (مثال: هزینه اقامت، پذیرایی، بنزین):"
    elif tone == "toxic":
        return "📌 <b>بابت چه غلطی پول دادی؟</b>\nاسم این خرج کوفتی رو بنویس (مثلاً: شکم‌چرونی رستوران، قلیون، عرق‌خوری، بنزین):"
    else:
        return "📌 <b>بابت چی خرج کردی داداش؟</b>\nیه اسم کوتاه بنویس ببینم (مثلاً: شام دیشب، بنزین ماشین، خرید سوپرمارکت):"

def msg_expense_amount_prompt(tone: str, title: str) -> str:
    title = _s(title)
    if tone == "formal":
        return f"🏷️ <b>شرح هزینه:</b> {title}\n\n💵 <b>مبلغ کل:</b>\nلطفاً مبلغ کل فاکتور را به تومان مرقوم فرمایید (مثال: 450,000 یا ۴۵۰ هزار):"
    elif tone == "toxic":
        return f"🏷️ <b>بابت:</b> {title}\n\n💵 <b>چقدر پیاده شدی حاجی؟</b>\nمبلغ خرج رو به تومان بفرست ببینم چقدر رفتی تو پاچه (مثلا: 450000 یا ۴۵۰ هزار):"
    else:
        return f"🏷️ <b>بابت:</b> {title}\n\n💵 <b>چقدر خرج برداشته مشتی؟</b>\nمبلغ کل رو به تومان بفرست (مثلاً: 450000 یا ۴۵۰ هزار تومان):"

def msg_expense_payer_prompt(tone: str, title: str, amt_str: str) -> str:
    title = _s(title)
    if tone == "formal":
        return f"🏷️ <b>هزینه:</b> {title}\n💰 <b>مبلغ:</b> {amt_str}\n\n👤 <b>شخص پرداخت‌کننده:</b>\nلطفاً عضوی که وجه فوق را تأمین نموده‌اند انتخاب فرمایید:"
    elif tone == "toxic":
        return f"🏷️ <b>هزینه:</b> {title}\n💰 <b>مبلغ:</b> {amt_str}\n\n👤 <b>کدوم دیوثی کارت کشیده؟</b>\nکی دست به جیب شده این پول رو داده؟ انتخابش کن:"
    else:
        return f"🏷️ <b>بابت:</b> {title}\n💰 <b>مبلغ:</b> {amt_str}\n\n👤 <b>کی دست به جیب شده؟</b>\nشخصی که حساب کرده رو انتخاب کن رفیق:"

def msg_expense_shares_prompt(tone: str, title: str, amt_str: str, payer_name: str) -> str:
    title = _s(title)
    payer_name = _s(payer_name)
    if tone == "formal":
        return (
            f"🏷️ <b>هزینه:</b> {title}\n💰 <b>مبلغ:</b> {amt_str}\n👤 <b>پرداخت‌کننده:</b> {payer_name}\n\n"
            "👥 <b>تسهیم هزینه:</b>\nلطفاً اعضای سهیم در این هزینه را مشخص فرمایید (به‌صورت پیش‌فرض بین همگان مساوی تقسیم می‌گردد):"
        )
    elif tone == "toxic":
        return (
            f"🏷️ <b>هزینه:</b> {title}\n💰 <b>مبلغ:</b> {amt_str}\n👤 <b>کارت‌کشنده:</b> {payer_name}\n\n"
            "👥 <b>کیا سگ‌خور این خرج بودن؟</b>\nکیا باید شل کنن دنگ بدن؟ پیش‌فرض همه تیک خوردن، اگه کسی مفت‌خوری نکرده تیکشو بردار:"
        )
    else:
        return (
            f"🏷️ <b>بابت:</b> {title}\n💰 <b>مبلغ:</b> {amt_str}\n👤 <b>حساب‌کننده:</b> {payer_name}\n\n"
            "👥 <b>این خرج دنگ کیاست؟</b>\nپیش‌فرض همه بچه‌ها انتخاب شدن. اگه کسی نبوده تیکشو بردار و دکمه تایید رو بزن:"
        )

def msg_expense_saved(tone: str, title: str, amt_str: str, payer_name: str, count: int, base_share_str: str, involved_text: str) -> str:
    title = _s(title)
    payer_name = _s(payer_name)
    involved_text = _s(involved_text)
    if tone == "formal":
        return (
            f"✅ <b>هزینه با موفقیت در دفاتر ثبت گردید.</b>\n\n"
            f"🏷️ شرح: <b>{title}</b>\n"
            f"💰 مبلغ کل: <b>{amt_str}</b>\n"
            f"👤 پرداخت‌کننده محترم: <b>{payer_name}</b>\n"
            f"👥 اعضای سهیم ({count} نفر - سهم سرانه ~ {base_share_str}):\n"
            f"<i>{involved_text}</i>\n"
        )
    elif tone == "toxic":
        return (
            f"✅ <b>خرجت ثبت شد لاشی!</b> 🧨\n\n"
            f"🏷️ بابت: <b>{title}</b>\n"
            f"💰 سر جمع پیاده شدی: <b>{amt_str}</b>\n"
            f"👤 خرپول جمع: <b>{payer_name}</b>\n"
            f"👥 شریک‌های جرم ({count} نفر - سهم هر لاشی ~ {base_share_str}):\n"
            f"<i>{involved_text}</i>\n"
        )
    else:
        return (
            f"✅ <b>دمت گرم، خرجت ثبت شد مشتی!</b> 🌸\n\n"
            f"🏷️ بابت: <b>{title}</b>\n"
            f"💰 چقدر پیاده شدی: <b>{amt_str}</b>\n"
            f"👤 کی حساب کرد: <b>{payer_name}</b>\n"
            f"👥 سهم بچه‌ها ({count} نفر - سهم هر نفر ~ {base_share_str}):\n"
            f"<i>{involved_text}</i>\n"
        )

# ----------------- پیام‌های گزارش و تسویه حساب -----------------
def render_settlement_title(tone: str, group_title: str) -> str:
    group_title = _s(group_title)
    if tone == "formal":
        return f"⚖️ <b>صورت‌حساب نهایی و دستورالعمل تسویه گروه «{group_title}»</b>\n"
    elif tone == "toxic":
        return f"⚖️ <b>فرمول حساب‌کشی و صاف کردن بدهی‌های «{group_title}»</b> 🔞\n"
    else:
        return f"⚖️ <b>حساب کتاب تسویه دنگ‌های گروه «{group_title}»</b>\n"

def render_reminder_msg(tone: str, creditor_name: str, debtor_name: str, amount: int, card_info: str) -> str:
    creditor_name = _s(creditor_name)
    debtor_name = _s(debtor_name)
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
    else:
        return (
            f"🔔 <b>سلام داداش، یه یادآوری کوچیک دنگ!</b>\n\n"
            f"سلام <b>{debtor_name}</b> گل! رفیقمون <b>{creditor_name}</b> یادآوری فرستاده که مبلغ <b>{amt_str}</b> از دنگت باقی مونده.\n\n"
            f"💳 <b>شماره کارتش اینه:</b>\n{card_info}\n\n"
            f"دمت گرم، هر وقت تونستی واریز کن حساب‌ها صاف شه و دورهمی حلال باشه 🌺"
        )

def render_payment_notice(tone: str, debtor_name: str, creditor_name: str, amount: int) -> str:
    debtor_name = _s(debtor_name)
    creditor_name = _s(creditor_name)
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
            f"🎉 <b>مژده بده! بالاخره این خسیس دست به جیب شد!</b>\n\n"
            f"هوی <b>{creditor_name}</b>! این پفیوز <b>{debtor_name}</b> اعلام کرد که <b>{amt_str}</b> ریخته به حسابت!\n\n"
            f"حسابت رو چک کن ببین راست میگه یا چاخان کرده پولتو بالا کشیده! 👀"
        )
    else:
        return (
            f"💸 <b>اعلام واریزی دنگ!</b>\n\n"
            f"سلام <b>{creditor_name}</b> جان،\n"
            f"<b>{debtor_name}</b> اعلام کرد که مبلغ <b>{amt_str}</b> رو برات کارت به کارت کرده.\n\n"
            f"یه سر به حسابت بزن ببین اوکیه یا نه رفیق ✨"
        )

# ----------------- پیام‌های صفر کردن و گزارش خالی -----------------
def render_no_expenses_msg(tone: str, title: str) -> str:
    title = _s(title)
    if tone == "formal":
        return (
            f"📊 <b>گزارش مالی گروه «{title}»:</b>\n\n"
            "📭 در حال حاضر هیچ فاکتور هزینه‌ای در دوره جاری ثبت نگردیده است.\n"
            "جهت درج اسناد مالی، گزینه «💸 ثبت هزینه جدید» را انتخاب فرمایید."
        )
    elif tone == "toxic":
        return (
            f"📊 <b>حساب‌کتاب پاتوق «{title}»:</b>\n\n"
            "📭 هیچ غلطی نکردین و پولی خرج نشده یا همه رو صاف کردین رفت پی کارش!\n"
            "دست به جیب بشین یه خرجی ثبت کنین ببینم:"
        )
    else:
        return (
            f"📊 <b>وضعیت خرج‌های دورهمی «{title}»:</b>\n\n"
            "📭 فعلاً هیچ خرج فعالی تو این دوره ثبت نشده رفقا ☕\n"
            "اگه جایی پیاده شدی یا خریدی کردی، از دکمه زیر دنگتو ثبت کن:"
        )

def render_all_settled_msg(tone: str, title: str) -> str:
    title = _s(title)
    prefix = render_settlement_title(tone, title)
    if tone == "formal":
        return (
            f"{prefix}\n"
            "🎉 <b>کلیه حساب‌های دوره جاری متوازن و تسویه می‌باشد.</b>\n"
            "هیچ‌گونه بدهی معوقه‌ای میان اعضا در دفاتر ثبت نگردیده است."
        )
    elif tone == "toxic":
        return (
            f"{prefix}\n"
            "🎉 <b>عجبا! هیچ لاشی‌ای به اون‌یکی بدهکار نیست!</b>\n"
            "یا همه‌تون گدا شدید دست به جیب نمیشید، یا بالاخره حسابا صاف شده! برین پی کارتون 🥳"
        )
    else:
        return (
            f"{prefix}\n"
            "🎉 <b>ایول! حساب همه بچه‌ها صافه صافه!</b>\n"
            "هیچ‌کس به اون‌یکی بدهکار نیست و دورهمی حلال شد. دمتون گرم 🌸"
        )

def msg_zero_confirm(tone: str, title: str) -> str:
    title = _s(title)
    if tone == "formal":
        return (
            f"⚠️ <b>تأییدیه بستن دوره مالی گروه «{title}»</b>\n\n"
            "آیا اطمینان دارید که مایل به تسویه کامل دفاتر و صفر کردن حساب‌ها می‌باشید؟\n\n"
            "• وضعیت تمام هزینه‌های دوره به «تسویه شده» تغییر خواهد کرد.\n"
            "• بدهی و طلب تمام اعضا صفر خواهد شد.\n"
            "• سوابق در بخش تاریخچه محفوظ خواهد ماند."
        )
    elif tone == "toxic":
        return (
            f"⚠️ <b>می‌خوای حسابای «{title}» رو صفر کنی؟</b>\n\n"
            "مطمئنی همه لاشیا دنگشونو دادن یا سرت کلاه گذاشتن؟\n\n"
            "• اگه تایید کنی، کل بدهیا پاک میشه و میره تو تاریخچه!\n"
            "• حساب همه صفر میشه از اول!\n"
            "بزنم صاف شه یا نه؟"
        )
    else:
        return (
            f"⚠️ <b>صفر کردن حساب‌های «{title}»</b>\n\n"
            "داداش مطمئنی همه دنگاشونو دادن و می‌خوای دوره رو ببندی؟\n\n"
            "• با زدن تایید، حساب همه صفر میشه و برای خریدهای بعدی از نو شروع می‌کنیم.\n"
            "• سابقه خریدهای قبلی هم تو بخش تاریخچه می‌مونه."
        )

def msg_zero_done(tone: str, title: str, settled_count: int) -> str:
    title = _s(title)
    if tone == "formal":
        return (
            f"🎉 <b>دوره مالی گروه «{title}» با موفقیت مختومه و تسویه گردید.</b>\n\n"
            f"تعداد {settled_count} فقره سند مالی بایگانی شد و دفاتر از نو گشوده شدند."
        )
    elif tone == "toxic":
        return (
            f"🎉 <b>حسابای «{title}» صاف شد رفت قاطی باقالیا!</b>\n\n"
            f"تعداد {settled_count} تا خرج و فاکتور کوفتی بایگانی شد! حالا برین دوباره ولخرجی کنین 🧨"
        )
    else:
        return (
            f"🎉 <b>حساب‌های گروه «{title}» با موفقیت صفر شد!</b>\n\n"
            f"دم همگی گرم! تعداد {settled_count} تا خرج تسویه و بایگانی شد.\n"
            "دوره جدید از صفر شروع شد مشتی 🌸"
        )

# ----------------- پیام‌های انتخاب رندوم غذا -----------------
def msg_food_picker_intro(tone: str, group_title: str, items: list[str]) -> str:
    group_title = _s(group_title)
    if items: items = [_s(x) for x in items]
    if not items:
        if tone == "formal":
            return (
                f"🍕 <b>سامانه قرعه‌کشی و انتخاب رندوم غذا برای گروه «{group_title}»:</b>\n\n"
                "📭 در حال حاضر هیچ گزینه‌ای در فهرست ثبت نشده است.\n\n"
                "✍️ لطفاً نام غذاها یا رستوران‌های مدنظر خود را به نوبت ارسال فرمایید (یا با ویرگول/خط جدید جدا کنید):\n"
                "<i>(مثال: پیتزا پپرونی، قورمه‌سبزی، چلوکباب، سالاد سزار...)</i>"
            )
        elif tone == "toxic":
            return (
                f"🍕 <b>چرخونه کوفت‌شناسی گنگ «{group_title}»!</b> 🍽️\n\n"
                "📭 هنوز هیچ غلطی نکردین و لیست کوفتی خالیه!\n\n"
                "✍️ اسم غذاهایی که مدنظرتونه رو دونه دونه بنالید تا بندازیم تو چرخونه:\n"
                "<i>(مثلاً: پیتزا، کباب، فلافل سر کوچه، نون پنیر، سوشی...)</i>"
            )
        else:
            return (
                f"🍕 <b>گردونه چی بخوریم برای دورهمی «{group_title}»!</b> 😋\n\n"
                "📭 هنوز غذایی به لیست اضافه نکردی رفیق!\n\n"
                "✍️ اسم غذاها یا رستوران‌هایی که تو فکرتونه رو دونه دونه بفرست (یا با کاما/خط بعدی جدا کن):\n"
                "<i>(مثلاً: پیتزا، قورمه‌سبزی، جوجه کباب، برگر، سوشی، املت مشتی...)</i>"
            )
    else:
        items_list = "\n".join([f"{i+1}️⃣ <b>{name}</b>" for i, name in enumerate(items)])
        if tone == "formal":
            return (
                f"🍕 <b>فهرست غذاهای پیشنهادی گروه «{group_title}» ({len(items)} مورد):</b>\n\n"
                f"{items_list}\n\n"
                "✍️ می‌توانید گزینه بعدی را ارسال فرمایید، یا در صورت تکمیل گزینه‌ها، دکمه «🎲 قرعه‌کشی کن» را انتخاب نمایید:"
            )
        elif tone == "toxic":
            return (
                f"🍕 <b>لیست کوفت‌جات پیشنهادی «{group_title}» ({len(items)} تا):</b>\n\n"
                f"{items_list}\n\n"
                "✍️ باز هم کوفت دیگه‌ای می‌خوای بنویس، وگرنه دکمه قرعه‌کشی رو بزن ببینیم چه خاکی باید تو سرمون کنیم:"
            )
        else:
            return (
                f"🍕 <b>لیست غذاهای پیشنهادی دورهمی «{group_title}» ({len(items)} تا):</b>\n\n"
                f"{items_list}\n\n"
                "✍️ غذای بعدی رو بفرست، یا اگر تموم شد دکمه قرعه‌کشی رو بزن تا ببینیم قرعه به نام چی میفته:"
            )

def msg_food_winner(tone: str, group_title: str, winner: str, items_count: int) -> str:
    group_title = _s(group_title)
    winner = _s(winner)
    if tone == "formal":
        return (
            f"🎲 <b>نتیجه قرعه‌کشی و انتخاب رندوم غذا:</b>\n"
            f"📁 گروه: <b>{group_title}</b>\n\n"
            f"از میان {items_count} گزینه پیشنهادی، غذای منتخب عبارت است از:\n\n"
            f"🌟 <b>«{winner}»</b> 🌟\n\n"
            "نوش جان و اوقاتی خوش را در کنار یکدیگر آرزومندیم. 🌺"
        )
    elif tone == "toxic":
        return (
            f"🎲 <b>بالاخره این گردونه لعنتی چرخید و قرعه در اومد!</b> 🧨\n"
            f"📁 پاتوق: <b>{group_title}</b>\n\n"
            f"💩 امروز باید این کوفت رو زهرمار کنید:\n\n"
            f"🔥 <b>«{winner}»</b> 🔥\n\n"
            f"از بین {items_count} تا کوفت و زهرمار این برنده شد! هر کی زر بزنه و بهونه بیاره دیوثه! برین کوفت کنین دهنتون سرویس نشه! 🖕"
        )
    else:
        return (
            f"🎲 <b>گردونه چرخید و قرعه افتاد به نام:</b>\n"
            f"📁 دورهمی: <b>{group_title}</b>\n\n"
            f"🔥 <b>«{winner}»</b> 🔥\n\n"
            f"از بین {items_count} تا گزینه وسوسه‌انگیز، این انتخاب شد! بزنید بر بدن نوش جونتون 😋\n"
            "دیگه هیشکی حق نداره بهونه بیاره و غر بزنه رفقا!"
        )
