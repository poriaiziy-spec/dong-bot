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


def parse_quantity(text: str | None) -> float | None:
    """
    تبدیل متن تعداد یا مقدار به عدد اعشاری یا صحیح مثبت.
    پشتیبانی از ارقام فارسی و انگلیسی، ممیز و اعشار (مانند 4 یا ۱.۵ یا ۲٫۵).
    """
    if not text:
        return None
    cleaned = str(text).strip()
    if cleaned.startswith("-") or "منفی" in cleaned:
        return None
    for i, char in enumerate(PERSIAN_DIGITS):
        cleaned = cleaned.replace(char, str(i))
    for i, char in enumerate(ARABIC_DIGITS):
        cleaned = cleaned.replace(char, str(i))
    cleaned = cleaned.replace("٫", ".").replace("/", ".").replace("،", "")
    for word in ["عدد", "بسته", "کیلوگرم", "کیلو", "دونه", "تا", "قوطی", "بطری", "جعبه"]:
        cleaned = re.sub(rf"\b{word}\b|{word}", "", cleaned).strip()
    try:
        val = float(cleaned)
        if val > 0:
            return val
    except ValueError:
        pass
    return None


def format_quantity(qty: float) -> str:
    """فرمت‌بندی زیبای تعداد یا مقدار"""
    if qty.is_integer():
        return f"{int(qty)} عدد"
    return f"{qty:g}"


def parse_amount_or_quantity_expression(text: str | None) -> tuple[int | None, dict | None]:
    """
    تحلیل ورودی مبلغ، با پشتیبانی از:
    ۱. مبالغ ساده (مثل 140000 یا ۱۴۰ هزار)
    ۲. فرمول ضرب قیمت واحد در تعداد (مثل 35000 * 4 یا ۳۵۰۰۰ × ۴ یا 35k * 4 یا ۴ تا ۳۵ هزار یا 35000 ضربدر 4 یا 35000 4)
    
    خروجی: (total_amount, detail_dict)
    detail_dict = {"unit_price": int, "quantity": float, "total": int} یا None اگر مبلغ ساده باشد.
    """
    if not text:
        return None, None
        
    raw = str(text).strip()
    if raw.startswith("-") or "منفی" in raw:
        return None, None

    # بررسی جداکننده‌های ضرب و تعداد
    patterns = [
        r"\s*[\*×xX]\s*",
        r"\s+ضربدر\s+",
        r"\s+ضرب\s+در\s+",
        r"\s+تا\s+",
        r"\s+عدد\s+",
        r"\s+دونه\s+"
    ]
    
    for pat in patterns:
        parts = re.split(pat, raw, maxsplit=1)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            p1, p2 = parts[0].strip(), parts[1].strip()
            
            # حالت ۱: p1 قیمت واحد و p2 تعداد
            u1 = clean_amount_input(p1)
            q2 = parse_quantity(p2)
            if u1 and q2 and u1 > 0 and q2 > 0:
                tot = int(round(u1 * q2))
                return tot, {"unit_price": u1, "quantity": q2, "total": tot}
                
            # حالت ۲: p1 تعداد و p2 قیمت واحد (مثل: ۴ تا ۳۵ هزار)
            q1 = parse_quantity(p1)
            u2 = clean_amount_input(p2)
            if q1 and u2 and q1 > 0 and u2 > 0:
                tot = int(round(u2 * q1))
                return tot, {"unit_price": u2, "quantity": q1, "total": tot}

    # بررسی ۲ بخش با فاصله (مثل: "35000 4" یا "4 35000")
    space_parts = raw.split()
    if len(space_parts) == 2:
        p1, p2 = space_parts[0], space_parts[1]
        u1 = clean_amount_input(p1)
        q2 = parse_quantity(p2)
        if u1 and q2 and u1 > 0 and q2 > 0:
            tot = int(round(u1 * q2))
            return tot, {"unit_price": u1, "quantity": q2, "total": tot}

        q1 = parse_quantity(p1)
        u2 = clean_amount_input(p2)
        if q1 and u2 and q1 > 0 and u2 > 0:
            tot = int(round(u2 * q1))
            return tot, {"unit_price": u2, "quantity": q1, "total": tot}

    # در غیر این صورت به عنوان مبلغ معمولی تمیزکاری شود
    simple_val = clean_amount_input(raw)
    if simple_val and simple_val > 0:
        return simple_val, None

    return None, None


def parse_single_shopping_line(line: str) -> dict | None:
    """
    تحلیل یک سطر تکی از لیست خرید و استخراج:
    نام کالا، مقدار/تعداد، قیمت واحد و قیمت کل
    """
    if not line:
        return None
    raw = str(line).strip()
    if not raw:
        return None

    # حذف پیشوندهای شمارشی و بولت‌ها (مانند: 1. یا 1- یا 1) یا - یا * یا •)
    raw = re.sub(r"^[\s\d]+[\.\-\)\:]\s*", "", raw).strip()
    raw = re.sub(r"^[\*\-\•\·\+\#\>\~]\s*", "", raw).strip()
    if not raw:
        return None

    parts = raw.split()
    if not parts:
        return None

    units_keywords = [
        "تا", "عدد", "کیلو", "بسته", "دانه", "بطری", "جعبه",
        "شانه", "کیلوگرم", "دست", "قوطی", "پاکت", "لیتر"
    ]

    # ۱. بررسی حالت نام + قیمت + تعداد یا نام + تعداد + قیمت (حداقل ۳ یا ۴ بخش)
    if len(parts) >= 3:
        # اگر کلمه آخر یکی از واحدهای شمارش است (مثل: روغن ۴۵۰۰۰ ۲ تا)
        if parts[-1] in units_keywords and len(parts) >= 4:
            potential_qty = parse_quantity(parts[-2])
            potential_unit = clean_amount_input(parts[-3])
            if potential_qty and potential_unit and potential_qty > 0 and potential_unit >= 1000:
                name = " ".join(parts[:-3]).strip()
                if name:
                    tot = int(round(potential_unit * potential_qty))
                    return {"item_name": name, "quantity": potential_qty, "unit_price": potential_unit, "total_price": tot}

        # بررسی فرمت «چیپس 35000 4» (قیمت و سپس تعداد)
        potential_qty = parse_quantity(parts[-1])
        potential_unit = clean_amount_input(parts[-2])
        if potential_qty and potential_unit and potential_qty > 0 and potential_unit >= 1000:
            name = " ".join(parts[:-2]).strip()
            if name:
                tot = int(round(potential_unit * potential_qty))
                return {"item_name": name, "quantity": potential_qty, "unit_price": potential_unit, "total_price": tot}

        # بررسی فرمت برعکس «شیر ۲ 35000» (تعداد و سپس قیمت)
        potential_qty_rev = parse_quantity(parts[-2])
        potential_unit_rev = clean_amount_input(parts[-1])
        if potential_qty_rev and potential_unit_rev and potential_qty_rev > 0 and potential_unit_rev >= 1000:
            name = " ".join(parts[:-2]).strip()
            if name:
                tot = int(round(potential_unit_rev * potential_qty_rev))
                return {"item_name": name, "quantity": potential_qty_rev, "unit_price": potential_unit_rev, "total_price": tot}

    # ۲. بررسی نام + مقدار یا نام + قیمت (حداقل ۲ بخش)
    if len(parts) >= 2:
        last = parts[-1]
        prev = parts[-2]
        if last in units_keywords:
            qty = parse_quantity(prev)
            if qty and qty > 0:
                name = " ".join(parts[:-2]).strip()
                if name:
                    return {"item_name": name, "quantity": qty, "unit_price": 0, "total_price": 0}

        # اگر بخش آخر یک مقدار پولی است (>= 1000 تومان)
        num_price = clean_amount_input(last)
        if num_price and num_price >= 1000:
            name = " ".join(parts[:-1]).strip()
            if name:
                return {"item_name": name, "quantity": 1.0, "unit_price": num_price, "total_price": num_price}

        # اگر بخش آخر عدد ساده است (مقدار/تعداد)
        qty = parse_quantity(last)
        if qty and qty > 0:
            name = " ".join(parts[:-1]).strip()
            if name:
                return {"item_name": name, "quantity": qty, "unit_price": 0, "total_price": 0}

    # ۳. پیش‌فرض: کالا بدون قیمت و با مقدار پیش‌فرض ۱
    return {"item_name": raw, "quantity": 1.0, "unit_price": 0, "total_price": 0}


def parse_bulk_shopping_text(raw_text: str | None) -> list[dict]:
    """
    تحلیل هوشمند و تفکیک متن یکپارچه لیست خرید به اقلام مجزا
    پشتیبانی از تفکیک خطوط (Enter)، بولت‌ها و کاما/ویرگول فارسی
    """
    if not raw_text:
        return []

    items = []
    lines = str(raw_text).strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # تفکیک سطرهای دارای ویرگول یا کاما
        sub_parts = re.split(r"[،,;]+", line)
        for part in sub_parts:
            part = part.strip()
            if not part:
                continue
            parsed = parse_single_shopping_line(part)
            if parsed and parsed.get("item_name"):
                items.append(parsed)

    return items

