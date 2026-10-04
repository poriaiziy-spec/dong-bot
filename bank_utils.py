# دیکشنری پیش‌شماره‌های کارت‌های بانکی ایران
IRANIAN_BANKS = {
    "603799": "بانک ملی",
    "589210": "بانک سپه",
    "627648": "بانک صادرات",
    "627961": "بانک صنعت و معدن",
    "603770": "بانک کشاورزی",
    "628023": "بانک مسکن",
    "627760": "پست بانک",
    "502908": "بانک توسعه تعاون",
    "627412": "بانک اقتصاد نوین",
    "622106": "بانک پارسیان",
    "502229": "بانک پاسارگاد",
    "639607": "بانک سرمایه",
    "636214": "بانک آینده",
    "627381": "بانک انصار",
    "610433": "بانک ملت",
    "627353": "بانک تجارت",
    "505416": "بانک گردشگری",
    "505785": "بانک ایران زمین",
    "639346": "بانک سینا",
    "585983": "بانک تجارت",
    "863588": "بانک سامان",
    "621986": "بانک سامان",
    "505801": "بانک کوثر",
    "504706": "بانک شهر",
    "606373": "بلو بانک (Blu) / مهر ایران",
    "502938": "بانک دی",
    "504172": "بانک رسالت",
    "639599": "بانک قوامین",
    "636949": "بانک حکمت"
}

def detect_bank_name(card_number: str | None) -> str | None:
    """تشخیص نام بانک از روی ۶ رقم اول کارت"""
    if not card_number:
        return None
    clean_card = "".join(filter(str.isdigit, str(card_number)))
    if len(clean_card) >= 6:
        prefix = clean_card[:6]
        return IRANIAN_BANKS.get(prefix)
    return None

def format_card_number(card_number: str | None) -> str:
    """فرمت شماره کارت به‌صورت ۴ رقم ۴ رقم (مثال: ۶۰۳۷-۹۹۱۱-۲۲۳۳-۴۴۵۵)"""
    if not card_number:
        return "ثبت نشده"
    clean = "".join(filter(str.isdigit, str(card_number)))
    if len(clean) == 16:
        return f"{clean[:4]}-{clean[4:8]}-{clean[8:12]}-{clean[12:]}"
    return str(card_number)

def clean_card_input(text: str | None) -> str | None:
    """پاکسازی و اعتبارسنجی شماره کارت (۱۶ رقم)"""
    if not text:
        return None
    text_str = str(text).strip()
    # تبدیل ارقام فارسی و عربی
    for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹"):
        text_str = text_str.replace(c, str(i))
    for i, c in enumerate("٠١٢٣٤٥٦٧٨٩"):
        text_str = text_str.replace(c, str(i))
    clean = "".join(filter(str.isdigit, text_str))
    if len(clean) == 16:
        return clean
    return None
