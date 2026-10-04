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
    'pouria': 'پوریا', 'poria': 'پوریا', 'poorya': 'پوریا', 'mohammad': 'محمد', 'mamad': 'محمد',
    'mohamad': 'محمد', 'mohammadreza': 'محمدرضا', 'hossein': 'حسین', 'hosein': 'حسین', 'hassan': 'حسن',
    'hasan': 'حسن', 'amir': 'امیر', 'amirhossein': 'امیرحسین', 'amirali': 'امیرعلی', 'mehdi': 'مهدی',
    'mahdi': 'مهدی', 'sara': 'سارا', 'sarah': 'سارا', 'zahra': 'زهرا', 'maryam': 'مریم', 'mahsa': 'مهسا',
    'nima': 'نیما', 'sina': 'سینا', 'arash': 'آرش', 'saman': 'سامان', 'omid': 'امید',
    'farhad': 'فرهاد', 'hamed': 'حامد', 'hamid': 'حمید', 'saeed': 'سعید', 'said': 'سعید',
    'saeid': 'سعید', 'vahid': 'وحید', 'arman': 'آرمان', 'danial': 'دانیال', 'daniel': 'دانیال',
    'milad': 'میلاد', 'pedram': 'پدرام', 'shayan': 'شایان', 'kaveh': 'کاوه', 'babak': 'بابک',
    'behnam': 'بهنام', 'behzad': 'بهزاد', 'bahram': 'بهرام', 'bijan': 'بیژن', 'navid': 'نوید',
    'fatemeh': 'فاطمه', 'fati': 'فاطمه', 'narges': 'نرگس', 'parisa': 'پریسا', 'shirin': 'شیرین',
    'roya': 'رویا', 'elaheh': 'الهه', 'elahe': 'الهه', 'mona': 'مونا', 'sahar': 'سحر',
    'yasaman': 'یاسمن', 'yasi': 'یاسمن', 'aida': 'آیدا', 'ayda': 'آیدا', 'niloufar': 'نیلوفر',
    'niloofar': 'نیلوفر', 'elham': 'الهام', 'parham': 'پرهام', 'bardia': 'بردیا', 'radin': 'رادین',
    'sam': 'سام', 'sohrab': 'سهراب', 'shahram': 'شهرام', 'shahab': 'شهاب', 'erfan': 'عرفان',
    'sajjad': 'سجاد', 'soheil': 'سهیل', 'asal': 'عسل', 'negin': 'نگین', 'taraneh': 'ترانه',
    'behnaz': 'بهناز', 'parniyan': 'پرنیان', 'daryoosh': 'داریوش', 'dariush': 'داریوش', 'kourosh': 'کوروش',
    'korosh': 'کوروش', 'cyrus': 'کوروش', 'siamak': 'سیامک', 'peyman': 'پیمان', 'payam': 'پیام',
    'ashkan': 'اشکان', 'ehsan': 'احسان', 'iman': 'ایمان', 'farzin': 'فرزین', 'farshid': 'فرشید',
    'kamran': 'کامران', 'fariborz': 'فریبرز', 'mehran': 'مهران', 'mehrdad': 'مهرداد', 'parsa': 'پارسا',
    'shahin': 'شاهین', 'shervin': 'شروین', 'soroush': 'سروش', 'sorush': 'سروش', 'matin': 'متین',
    'mobin': 'مبین', 'mostafa': 'مصطفی', 'morteza': 'مرتضی', 'davood': 'داوود', 'davoud': 'داوود',
    'behrouz': 'بهروز', 'majid': 'مجید', 'masoud': 'مسعود', 'masood': 'مسعود', 'artin': 'آرتین',
    'iliya': 'ایلیا', 'ilya': 'ایلیا', 'ghazal': 'غزل', 'negar': 'نگار', 'nazanin': 'نازنین',
    'neda': 'ندا', 'mitra': 'میترا', 'mahnaz': 'مهناز', 'marjan': 'مرجان', 'mina': 'مینا',
    'minoo': 'مینو', 'saba': 'صبا', 'sanaz': 'ساناز', 'sepideh': 'سپیده', 'pegah': 'پگاه',
    'parvaneh': 'پروانه', 'zeinab': 'زینب', 'somayeh': 'سمیه', 'atefeh': 'عاطفه', 'faezeh': 'فائزه',
    'hanieh': 'هانیه', 'samaneh': 'سمانه', 'reyhaneh': 'ریحانه', 'arian': 'آرین', 'aryan': 'آرین'
}

COMPOUND_PREFIXES = {'امیر', 'محمد', 'علی', 'سید', 'فاطمه', 'نازنین'}

def is_clean_persian_name(name: str | None) -> bool:
    """
    بررسی اینکه آیا نام ارائه شده یک نام تمیز، معتبر و فارسی است یا خیر.
    نام‌های لاتین خام (مانند poriA Eazi)، علائم عجیب، ایموجی یا نام‌های نامفهوم معتبر نیستند.
    """
    if not name or not isinstance(name, str):
        return False
    clean = name.strip()
    if len(clean) < 2 or len(clean) > 30:
        return False
    if clean.lower() in STOP_WORDS or clean in TITLES:
        return False
    # نباید شامل حروف انگلیسی باشد
    if re.search(r'[a-zA-Z]', clean):
        return False
    # باید حداقل شامل حروف الفبای فارسی باشد
    if not re.search(r'[\u0600-\u06FF]', clean):
        return False
    return True


def guess_meaningful_name(first_name: str | None, last_name: str | None = None, username: str | None = None) -> str | None:
    """
    حدس هوشمندانه نام معنادار و تمیز فارسی کاربر از روی پروفایل تلگرام.
    در صورت عدم وجود اسم معنادار فارسی، مقدار None برگردانده می‌شود تا مستقیماً از کاربر پرسیده شود.
    """
    # ۱. اولویت اول: بررسی نام در متن فارسی پروفایل
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

    # ۲. بررسی کلمات انگلیسی در first_name و last_name و تطابق با دیکشنری اسامی فارسی
    for text in [first_name or '', last_name or '']:
        if not text:
            continue
        clean = re.sub(r'[^a-zA-Z\s]', ' ', text)
        words = [w for w in clean.split() if len(w) >= 2]
        for w in words:
            low = w.lower()
            if low in PERSIAN_NAMES_MAP:
                return PERSIAN_NAMES_MAP[low]

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
    if res.lower() in STOP_WORDS or res in TITLES:
        return None
    return res

