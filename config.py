import os
from pathlib import Path
from dotenv import load_dotenv

# بارگذاری مقادیر از فایل .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# توکن ربات تلگرام
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# مسیر فایل دیتابیس SQLite
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "dong_bot.db"))

# پروکسی برای مواقعی که در ایران نیاز به اتصال به تلگرام دارید
# فرمت: socks5://127.0.0.1:10808 یا http://127.0.0.1:10809
PROXY_URL = os.getenv("PROXY_URL", "")
