import re
import html

def safe(text: str) -> str:
    """Escape HTML special characters for safe Telegram message rendering"""
    return html.escape(str(text)) if text else ""

# تبدیل ارقام فارسی و عربی به انگلیسی
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"

def clean_amount_input(text: str | None) -> int | None:
    """
    متن ورودی مبلغ را دریافت کرده و به عدد صحیح تبدیل می‌کند.
    پشتیبانی از اعداد فارسی، اعشار با ضریب (مثل 2.5k یا ۲.۵ میلیون)، ویرگول، کلمات تومان/ریال و k/m/هزار/میلیون.
    """
    if not text:
        return None
    
    text = str(text).strip()
    if text.startswith("-") or "منفی" in text:
        return None
    
    # تبدیل ارقام فارسی و عربی به انگلیسی
    for i, char in enumerate(PERSIAN_DIGITS):
        text = text.replace(char, str(i))
    for i, char in enumerate(ARABIC_DIGITS):
        text = text.replace(char, str(i))
    
    # تبدیل ممیز فارسی به نقطه اعشار
    text = text.replace("٫", ".").replace("/", ".")
    
    text_lower = text.lower()
    
    # حذف پسوندهای رایج تومان و ریال
    for suffix in ["تومان", "تومن", "ریال", "toman", "tooman", "t"]:
        text_lower = re.sub(rf"\b{suffix}\b|{suffix}$", "", text_lower).strip()
    
    # بررسی ضرایب هزار (k) و میلیون (m)
    multiplier = 1
    has_multiplier = False
    if "هزار" in text_lower or text_lower.endswith("k"):
        multiplier = 1_000
        has_multiplier = True
        text_lower = text_lower.replace("هزار", "").replace("k", "").strip()
    elif "میلیون" in text_lower or text_lower.endswith("m"):
        multiplier = 1_000_000
        has_multiplier = True
        text_lower = text_lower.replace("میلیون", "").replace("m", "").strip()

    if has_multiplier:
        # اگر ضریب دارد، ممکن است اعشار باشد مانند 2.5k یا 2,5 میلیون
        decimal_candidate = text_lower.replace(",", ".").strip()
        match = re.search(r"^\d+(\.\d+)?$", decimal_candidate)
        if match:
            try:
                val = int(round(float(match.group(0)) * multiplier))
                return val if val > 0 else None
            except ValueError:
                return None

    # استخراج فقط ارقام بدون ضریب اعشاری
    cleaned = re.sub(r"[^\d]", "", text_lower)
    if not cleaned:
        return None
        
    try:
        val = int(cleaned) * multiplier
        if val <= 0:
            return None
        return val
    except ValueError:
        return None


def format_amount(amount: float | int) -> str:
    """
    فرمت کردن عدد با جداکننده سه رقمی و پسوند تومان
    مثال: 1250000 -> ۱,۲۵۰,۰۰۰ تومان
    """
    amount_int = int(round(amount))
    formatted = f"{amount_int:,}"
    return f"{formatted} تومان"


def mention_user(user_id: int, full_name: str, username: str | None = None) -> str:
    """
    ایجاد لینک منشن برای کاربر در متن HTML تلگرام با ایمن‌سازی کامل
    """
    clean_name = safe(full_name or "کاربر")
    if username:
        return f'<a href="https://t.me/{username}">{clean_name}</a>'
    return f'<a href="tg://user?id={user_id}">{clean_name}</a>'
