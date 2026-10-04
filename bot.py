import asyncio
import logging
import os
import sys

# تنظیم خروجی کنسول روی UTF-8 در ویندوز
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import BOT_TOKEN, PROXY_URL
from database import init_db
from handlers import setup_routers
from motivational import start_daily_quote_scheduler

# تنظیم لاگ‌ها
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def start_health_check_server():
    """راه‌اندازی سرور وب سبک برای سازگاری با هاست‌های ابری رایگان مانند Render و HuggingFace"""
    port = int(os.getenv("PORT", "8080"))
    app = web.Application()
    app.router.add_get("/", lambda req: web.Response(text="Dong Telegram Bot is active and running 24/7!"))
    app.router.add_get("/health", lambda req: web.Response(text="OK"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 سرور پایش وضعیت (Health Check) روی پورت {port} فعال شد.")
    return runner

async def set_bot_commands(bot: Bot):
    """تنظیم منوی دستورات ربات در تلگرام"""
    commands = [
        BotCommand(command="start", description="🏠 شروع و منوی اصلی"),
        BotCommand(command="myname", description="👤 مشاهده و ویرایش نام من"),
        BotCommand(command="groups", description="👥 گروه‌های من"),
        BotCommand(command="newgroup", description="➕ ساخت گروه دنگ جدید"),
        BotCommand(command="cancel", description="❌ لغو عملیات جاری"),
        BotCommand(command="help", description="💡 راهنمای کار با ربات"),
        BotCommand(command="reset_all_data", description="🧹 ریست و پاکسازی کامل دیتابیس"),
    ]
    await bot.set_my_commands(commands)


async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error(
            "❌ توکن ربات تنظیم نشده است! لطفاً فایل .env را باز کرده و مقدار BOT_TOKEN را وارد کنید."
        )
        sys.exit(1)

    # مقداردهی اولیه دیتابیس SQLite
    await init_db()
    logger.info("✅ دیتابیس با موفقیت آماده‌سازی شد.")

    # سرور سبک وب برای زنده نگه داشتن در هاست‌های ابری
    web_runner = await start_health_check_server()

    # پشتیبانی از پروکسی در صورت نیاز
    session = None
    if PROXY_URL:
        logger.info(f"🌐 استفاده از پروکسی: {PROXY_URL}")
        session = AiohttpSession(proxy=PROXY_URL)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session
    )
    
    dp = Dispatcher()

    # مدیریت خطاهای پیش‌بینی‌نشده جهت جلوگیری از توقف ربات
    @dp.error()
    async def global_error_handler(event):
        logger.error(f"خطای مدیریت‌نشده: {event.exception}", exc_info=True)
        try:
            if hasattr(event, "update") and event.update:
                if event.update.callback_query:
                    await event.update.callback_query.answer("⚠️ خطایی رخ داد. لطفاً مجدداً تلاش کنید.", show_alert=True)
                elif event.update.message:
                    await event.update.message.answer("⚠️ متأسفانه در پردازش این دستور خطایی رخ داد. لطفاً با /start مجدداً امتحان کنید.")
        except Exception:
            pass

    # اتصال روت‌ها و هندلرهای ربات
    main_router = setup_routers()
    dp.include_router(main_router)

    # تنظیم دکمه‌های منو و نام و مشخصات ربات
    try:
        await set_bot_commands(bot)
        await bot.set_my_name(name="کافه دنگ ☕")
        await bot.set_my_description(description="☕ به کافه دنگ خوش آمدید!\nمدیریت هوشمند دنگ‌ها، تسهیم دقیق هزینه‌ها، یادآوری واریز و دورهمی رفقا.")
        await bot.set_my_short_description(short_description="کافه دنگ ☕ | مدیریت هوشمند دنگ و هزینه‌های مشترک")
    except Exception as e:
        logger.warning(f"عدم امکان تنظیم دستورات یا نام ربات در منو: {e}")

    logger.info("🚀 ربات کافه دنگ آماده به کار است و شروع به کار کرد...")
    
    # راه‌اندازی تسک پس‌زمینه ارسال جملات انگیزشی روزانه ساعت ۹ صبح
    scheduler_task = asyncio.create_task(start_daily_quote_scheduler(bot))

    try:
        # حذف پیام‌های صف قبل از استارت
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await web_runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ربات متوقف شد.")
