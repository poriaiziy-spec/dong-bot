import re

# تبدیل ارقام فارسی و عربی به انگلیسی
PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"

def clean_amount_input(text: str) -> int | None:
    """
    متن ورودی مبلغ را دریافت کرده و به عدد صحیح تبدیل می‌کند.
    پشتیبانی از اعداد فارسی، ویرگول، کلمات تومان/ریال و k/m/هزار/میلیون.
    """
    if not text:
        return None
    
    text = text.strip()
    
    # تبدیل ارقام فارسی به انگلیسی
    for i, char in enumerate(PERSIAN_DIGITS):
        text = text.replace(char, str(i))
    # تبدیل ارقام عربی به انگلیسی
    for i, char in enumerate(ARABIC_DIGITS):
        text = text.replace(char, str(i))
    
    text_lower = text.lower()
    
    # حذف پسوندهای رایج تومان و ریال
    for suffix in ["تومان", "تومن", "ریال", "toman", "tooman", "t"]:
        text_lower = re.sub(rf"\b{suffix}\b|{suffix}$", "", text_lower).strip()
    
    # بررسی ضرایب هزار (k) و میلیون (m)
    multiplier = 1
    if "هزار" in text_lower or text_lower.endswith("k"):
        multiplier = 1_000
        text_lower = text_lower.replace("هزار", "").replace("k", "").strip()
    elif "میلیون" in text_lower or text_lower.endswith("m"):
        multiplier = 1_000_000
        text_lower = text_lower.replace("میلیون", "").replace("m", "").strip()

    # استخراج فقط ارقام
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
    ایجاد لینک منشن برای کاربر در متن HTML تلگرام
    """
    clean_name = (full_name or "کاربر").replace("<", "&lt;").replace(">", "&gt;")
    if username:
        return f'<a href="https://t.me/{username}">{clean_name}</a>'
    return f'<a href="tg://user?id={user_id}">{clean_name}</a>'
