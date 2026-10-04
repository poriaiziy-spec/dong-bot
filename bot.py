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
        BotCommand(command="groups", description="👥 گروه‌های من"),
        BotCommand(command="newgroup", description="➕ ساخت گروه دنگ جدید"),
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

    # اتصال روت‌ها و هندلرهای ربات
    main_router = setup_routers()
    dp.include_router(main_router)

    # تنظیم دکمه‌های منو
    try:
        await set_bot_commands(bot)
    except Exception as e:
        logger.warning(f"عدم امکان تنظیم دستورات در منو: {e}")

    logger.info("🚀 ربات دنگ‌بگیر آماده به کار است و شروع به کار کرد...")
    
    try:
        # حذف پیام‌های صف قبل از استارت
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await web_runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ربات متوقف شد.")
