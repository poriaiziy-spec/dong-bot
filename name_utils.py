import re

TITLES = {
    'دکتر', 'مهندس', 'سید', 'سیده', 'حاجی', 'حاج', 'کربلایی', 'استاد', 'شیخ', 'آقا', 'آقای', 'خانم', 'دوشیزه',
    'dr', 'dr.', 'eng', 'mr', 'mrs', 'ms', 'miss', 'prof', 'engineer'
}

STOP_WORDS = {
    'user', 'telegram', 'unknown', 'admin', 'null', 'none', 'deleted', 'account', 'anonymous', 'bot',
    'test', 'member', 'کاربر', 'ناشناس', 'اکانت', 'دیلیت', 'تلگرام', 'تست', 'ادمین'
}

PERSIAN_NAMES_MAP = {
    'ali': 'علی', 'alireza': 'علیرضا', 'reza': 'رضا', 'puriya': 'پوریا', 'pooria': 'پوریا',
    'pouria': 'پوریا', 'poria': 'پوریا', 'mohammad': 'محمد', 'mamad': 'محمد', 'mohamad': 'محمد',
    'mohammadreza': 'محمدرضا', 'hossein': 'حسین', 'hosein': 'حسین', 'hassan': 'حسن', 'hasan': 'حسن',
    'amir': 'امیر', 'amirhossein': 'امیرحسین', 'amirali': 'امیرعلی', 'mehdi': 'مهدی', 'mahdi': 'مهدی',
    'sara': 'سارا', 'sarah': 'سارا', 'zahra': 'زهرا', 'maryam': 'مریم', 'mahsa': 'مهسا',
    'nima': 'نیما', 'sina': 'سینا', 'arash': 'آرش', 'saman': 'سامان', 'omid': 'امید',
    'farhad': 'فرهاد', 'hamed': 'حامد', 'saeed': 'سعید', 'said': 'سعید', 'arman': 'آرمان',
    'danial': 'دانیال', 'milad': 'میلاد', 'pedram': 'پدرام', 'shayan': 'شایان', 'kaveh': 'کاوه',
    'babak': 'بابک', 'behnam': 'بهنام', 'navid': 'نوید', 'fatemeh': 'فاطمه', 'fati': 'فاطمه',
    'narges': 'نرگس', 'parisa': 'پریسا', 'shirin': 'شیرین', 'roya': 'رویا', 'elaheh': 'الهه',
    'elahe': 'الهه', 'mona': 'مونا', 'sahar': 'سحر', 'yasaman': 'یاسمن', 'yasi': 'یاسمن',
    'aida': 'آیدا', 'ayda': 'آیدا', 'niloufar': 'نیلوفر', 'niloofar': 'نیلوفر', 'elham': 'الهام',
    'parham': 'پرهام', 'bardia': 'بردیا', 'radin': 'رادین', 'sam': 'سام', 'sohrab': 'سهراب',
    'shahram': 'شهرام', 'shahab': 'شهاب', 'erfan': 'عرفان', 'sajjad': 'سجاد', 'soheil': 'سهیل',
    'asal': 'عسل', 'negin': 'نگین', 'taraneh': 'ترانه', 'behnaz': 'بهناز', 'parniyan': 'پرنیان',
    'daryoosh': 'داریوش', 'dariush': 'داریوش', 'kourosh': 'کوروش', 'cyrus': 'کوروش', 'siamak': 'سیامک',
    'peyman': 'پیمان', 'payam': 'پیام', 'ashkan': 'اشکان', 'ehsan': 'احسان', 'iman': 'ایمان',
    'farzin': 'فرزین', 'farshid': 'فرشید', 'kamran': 'کامران', 'korosh': 'کوروش', 'fariborz': 'فریبرز'
}

COMPOUND_PREFIXES = {'امیر', 'محمد', 'علی', 'سید', 'فاطمه', 'نازنین'}

def guess_meaningful_name(first_name: str | None, last_name: str | None = None, username: str | None = None) -> str | None:
    """
    حدس هوشمندانه نام معنادار و تمیز کاربر از روی پروفایل تلگرام.
    در صورت عدم وجود اسم معنادار، مقدار None برگردانده می‌شود تا از کاربر پرسیده شود.
    """
    # ۱. اولویت اول: بررسی نام در متن فارسی
    for text in [first_name or '', last_name or '']:
        if not text:
            continue
        # حذف اموجی‌ها، تزیینات و کاراکترهای نامتعارف
        clean = re.sub(r'[^\w\s\u0600-\u06FF]', ' ', text)
        words = [w for w in clean.split() if len(w) >= 2]
        words = [w for w in words if w.lower() not in TITLES and w.lower() not in STOP_WORDS]
        p_words = [w for w in words if re.search(r'[\u0600-\u06FF]', w)]
        if p_words:
            # بررسی اسامی دو بخشی متداول (مثل امیرحسین، محمدرضا، نازنین زهرا)
            if len(p_words) >= 2 and p_words[0] in COMPOUND_PREFIXES:
                return f"{p_words[0]} {p_words[1]}"
            return p_words[0]

    # ۲. بررسی نام انگلیسی در first_name و last_name
    for text in [first_name or '', last_name or '']:
        if not text:
            continue
        clean = re.sub(r'[^a-zA-Z\s]', ' ', text)
        words = [w for w in clean.split() if len(w) >= 2]
        for w in words:
            low = w.lower()
            if low in PERSIAN_NAMES_MAP:
                return PERSIAN_NAMES_MAP[low]
        for w in words:
            low = w.lower()
            if low in TITLES or low in STOP_WORDS:
                continue
            # کلمه انگلیسی باید حداقل یک حرف صدادار داشته باشد تا نام معنادار باشد
            if len(w) >= 3 and re.search(r'[aeiouy]', low) and not re.match(r'^(user|test|admin|bot|none)', low):
                return w.capitalize()

    # ۳. بررسی یوزرنیم فقط در صورت تطابق دقیق با دیکشنری اسامی
    if username:
        clean_un = re.sub(r'[^a-zA-Z]', '', username).lower()
        for key, val in PERSIAN_NAMES_MAP.items():
            if len(key) >= 3 and key in clean_un:
                return val

    return None


def clean_input_name(text: str) -> str | None:
    """پاکسازی و اعتبارسنجی نام دستی وارد شده توسط کاربر"""
    if not text:
        return None
    # حذف اموجی و نمادهای اضافی
    clean = re.sub(r'[^\w\s\u0600-\u06FF]', '', text).strip()
    words = clean.split()
    if not words:
        return None
    res = " ".join(words[:2])  # حداکثر دو کلمه (مثلاً علی رضایی یا امیر حسین)
    if len(res) < 2 or len(res) > 30:
        return None
    if res.lower() in STOP_WORDS:
        return None
    return res
