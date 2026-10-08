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

# لیست شناسه‌های عددی ادمین‌های ربات جهت دسترسی به تنظیمات حساس و ریست
admin_env = os.getenv("ADMIN_IDS", "1207936155")
ADMIN_IDS = [int(x.strip()) for x in admin_env.split(",") if x.strip().isdigit()]

# کلید رمزنگاری سرتاسری دیتابیس در فضای ابری
ENCRYPTION_SECRET = os.getenv("DB_ENCRYPTION_KEY") or BOT_TOKEN or "dong_bot_master_vault_key_2026"

# آدرس سرور وب و مینی‌اپ تلگرام (HTTPS برای وب‌اپلیکیشن تلگرام الزامی است)
WEB_APP_URL = (os.getenv("WEB_APP_URL") or os.getenv("RENDER_EXTERNAL_URL") or "https://dong-bot-1.onrender.com").rstrip("/")

