import asyncio
import random
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot
import database as db

logger = logging.getLogger(__name__)

# منطقه زمانی رسمی ایران (تهران: UTC+03:30)
TEHRAN_TZ = timezone(timedelta(hours=3, minutes=30))

MOTIVATIONAL_QUOTES = [
    "امروز فرصت دوباره‌ایه تا یک قدم به رویاهات نزدیک‌تر بشی؛ پرانرژی و با لبخند شروع کن! ✨",
    "دنیا به انرژی قشنگ و لبخند تو نیاز داره؛ امروز رو پر از اتفاق‌های فوق‌العاده بساز! 🌸",
    "هیچ بادی نمی‌تونه درختی که ریشه‌اش محکمه رو بلرزونه؛ به توانایی‌های خودت ایمان داشته باش. 🌿",
    "بزرگ‌ترین معجزه‌ها از قدم‌های کوچیک شروع میشن؛ امروز با امید حرکت کن! 💫",
    "تو لایق بهترین اتفاق‌هایی؛ کافیه به تلاش و دل روشنت باور داشته باشی. صبحت پربرکت! 🌺",
    "روز نو، انرژی نو، انگیزه‌های نو! برو و از تک‌تک لحظه‌های امروز لذت ببر. ☀️",
    "آرامش و شادی از درون خودت شروع میشه؛ امروز رو با عشق و حس ناب زندگی کن. 💖",
    "سختی‌ها میان تا بهت یادآوری کنن چقدر قوی و شکست‌ناپذیری؛ بدرخش و پرقدرت جلو برو! 🚀",
    "امروز یه صفحه سفیده؛ زیباترین داستان ممکن رو توش بنویس. روزت سرشار از موفقیت! 🎨",
    "شکرگزاری برای چیزهای کوچیک، درهای اتفاق‌های بزرگ رو باز می‌کنه. امروز حال دلت عالی باشه! 🌻",
    "فرصت‌ها منتظر کسی نمیمونن؛ پاشو و امروز رو تبدیل به یک شاهکار کن! 🏆",
    "به خودت بگو: من از پسش برمیام! و مطمئن باش که موفق میشی. پرانرژی باش! 💪"
]

def get_daily_quote() -> str:
    """انتخاب یک جمله انگیزشی تصادفی و حال‌خوب‌کن"""
    return random.choice(MOTIVATIONAL_QUOTES)

def format_quote_message(quote: str) -> str:
    return (
        "☀️ <b>صبح بخیر و روزت پر از انرژی و اتفاق‌های قشنگ!</b> 🌸\n\n"
        f"✨ <i>«{quote}»</i>\n\n"
        "امیدوارم امروزت پر از لبخند، سلامتی و خیر و برکت باشه 🌺"
    )

async def broadcast_daily_quote(bot: Bot) -> int:
    """ارسال پیام صبحگاهی به تمام کاربران عضو ربات"""
    user_ids = await db.get_all_user_ids()
    if not user_ids:
        return 0

    quote = get_daily_quote()
    text = format_quote_message(quote)
    sent_count = 0

    for uid in user_ids:
        try:
            await bot.send_message(uid, text, parse_mode="HTML")
            sent_count += 1
            await asyncio.sleep(0.05)  # جلوگیری از محدودیت Flood تلگرام
        except Exception:
            pass

    logger.info(f"💌 پیام انگیزشی ۹ صبح برای {sent_count} کاربر با موفقیت ارسال شد.")
    return sent_count

async def start_daily_quote_scheduler(bot: Bot):
    """حلقه زمان‌بندی روزانه جهت ارسال خودکار پیام در ساعت ۹:۰۰ صبح به وقت تهران"""
    logger.info("⏰ سرویس زمان‌بندی پیام‌های انگیزشی ساعت ۹ صبح فعال شد.")
    while True:
        try:
            now = datetime.now(TEHRAN_TZ)
            target = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)

            sleep_seconds = (target - now).total_seconds()
            logger.info(f"⏳ پیام انگیزشی بعدی در ساعت ۰۹:۰۰ صبح ({sleep_seconds / 3600:.2f} ساعت دیگر) ارسال خواهد شد.")
            await asyncio.sleep(sleep_seconds)

            # ارسال پیام ساعت ۹ صبح
            await broadcast_daily_quote(bot)

            # ۶۰ ثانیه خواب جهت عبور از دقیقه ۰۰
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"خطا در زمان‌بندی پیام انگیزشی: {e}")
            await asyncio.sleep(60)
