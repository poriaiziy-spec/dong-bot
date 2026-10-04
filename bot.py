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
from cloud_db_sync import start_periodic_cloud_backup, backup_to_cloud

# تنظیم لاگ‌ها
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

_STATUS_HTML = """<!DOCTYPE html>
<html dir="rtl" lang="fa">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>کافه دنگ ☕ | وضعیت آنلاین</title>
    <style>
        body { font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 1rem; box-sizing: border-box; }
        .card { background: #1e293b; padding: 2.5rem 2rem; border-radius: 1.25rem; box-shadow: 0 20px 35px rgba(0,0,0,0.4); text-align: center; border: 1px solid #334155; max-width: 460px; width: 100%; }
        .badge { display: inline-flex; align-items: center; gap: 0.5rem; background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; padding: 0.4rem 1.2rem; border-radius: 9999px; font-weight: bold; margin-bottom: 1.2rem; font-size: 0.95rem; }
        .dot { width: 10px; height: 10px; background: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981; }
        h1 { margin: 0 0 0.75rem; font-size: 1.75rem; color: #f1f5f9; }
        p { color: #94a3b8; font-size: 0.95rem; line-height: 1.7; margin: 0.6rem 0; }
        .feature-box { background: #0f172a; border-radius: 0.75rem; padding: 1rem; margin: 1.5rem 0 0.5rem; text-align: right; border: 1px solid #334155; font-size: 0.9rem; }
        .feature-item { margin: 0.4rem 0; color: #cbd5e1; }
        .info { margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #334155; font-size: 0.8rem; color: #64748b; }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge"><span class="dot"></span> ۲۴/۷ آنلاین و فعال</div>
        <h1>ربات کافه دنگ ☕</h1>
        <p>سرور ابری فعال است و ربات تلگرام به صورت زنده و بلادرنگ در حال پردازش پیام‌ها و دنگ‌ها می‌باشد.</p>
        <div class="feature-box">
            <div class="feature-item">🔒 رمزنگاری نظامی AES-256 داده‌ها</div>
            <div class="feature-item">💓 مکانیزم زنده نگه‌داشتن مداوم (Keep-Alive)</div>
            <div class="feature-item">☁️ پشتیبان‌گیری خودکار در دیتابیس ابری</div>
        </div>
        <div class="info">Render Cloud Web Service • Anti-Sleep Guard Active</div>
    </div>
</body>
</html>"""

async def start_health_check_server():
    """راه‌اندازی سرور وب سبک برای سازگاری با هاست‌های ابری رایگان مانند Render و HuggingFace"""
    port = int(os.getenv("PORT", "8080"))
    app = web.Application()
    async def status_api_handler(req):
        try:
            import aiosqlite
            from config import DB_PATH
            from cloud_db_sync import _last_backup_status
            counts = {}
            async with aiosqlite.connect(DB_PATH) as db:
                for t in ["users", "groups", "group_members", "expenses", "user_cards"]:
                    async with db.execute(f"SELECT COUNT(*) FROM {t}") as cur:
                        counts[t] = (await cur.fetchone())[0]
            return web.json_response({"status": "online", "database": counts, "last_cloud_backup": _last_backup_status})
        except Exception as e:
            return web.json_response({"status": "error", "error": str(e)}, status=500)

    app.router.add_get("/", lambda req: web.Response(text=_STATUS_HTML, content_type="text/html", charset="utf-8"))
    app.router.add_get("/health", lambda req: web.Response(text="OK"))
    app.router.add_get("/api/status", status_api_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"🌐 سرور پایش وضعیت (Health Check) روی پورت {port} فعال شد.")
    return runner

async def start_keep_alive_task():
    """ارسال منظم پینگ دوره‌ای هر ۴ دقیقه به آدرس عمومی جهت جلوگیری از خوابیدن سرور رندر"""
    service_url = os.getenv("RENDER_EXTERNAL_URL") or "https://dong-bot-1.onrender.com"
    health_url = f"{service_url.rstrip('/')}/health"
    
    # تاخیر اولیه ۲۰ ثانیه‌ای برای اطمینان از استارت کامل سرور وب
    await asyncio.sleep(20)
    logger.info(f"🔄 تسک زنده نگه‌داشتن خودکار ۲۴ ساعته فعال شد (هدف: {health_url})")
    
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(health_url, timeout=aiohttp.ClientTimeout(total=25)) as resp:
                    if resp.status == 200:
                        logger.debug("💓 پینگ زنده نگه‌داشتن سرور با موفقیت انجام شد.")
        except Exception as e:
            logger.debug(f"Keep-alive ping notice: {e}")
        
        # هر ۴ دقیقه (۲۴۰ ثانیه) پینگ ارسال می‌شود تا از سقف ۱۵ دقیقه رندر خیلی فاصله داشته باشیم
        await asyncio.sleep(240)

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
        await bot.set_my_description(description="☕ به کافه دنگ خوش اومدی قشنگم!\nمن همراه و پارتنر صمیمی شما برای حساب‌کتاب دنگ‌ها، تسهیم دقیق هزینه‌ها، یادآوری و دورهمی‌های دلنشین هستم ❤️")
        await bot.set_my_short_description(short_description="کافه دنگ ☕❤️ | پارتنر صمیمی شما در مدیریت دنگ و دورهمی‌ها")
    except Exception as e:
        logger.warning(f"عدم امکان تنظیم دستورات یا نام ربات در منو: {e}")

    logger.info("🚀 ربات کافه دنگ آماده به کار است و شروع به کار کرد...")
    
    # راه‌اندازی تسک پس‌زمینه ارسال جملات انگیزشی روزانه ساعت ۹ صبح
    scheduler_task = asyncio.create_task(start_daily_quote_scheduler(bot))
    # راه‌اندازی تسک بکاپ‌گیری دوره‌ای هر ۵ دقیقه در پس‌زمینه
    periodic_sync_task = asyncio.create_task(start_periodic_cloud_backup(300))
    # راه‌اندازی تسک زنده نگه‌داشتن سرور رندر هر ۴ دقیقه (Keep-Alive ضد خوابیدن سرور)
    keep_alive_task = asyncio.create_task(start_keep_alive_task())

    try:
        # عدم حذف پیام‌های دریافتی تا پیام‌های ارسالی کاربر هنگام خواب موقت پردازش شوند
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot)
    finally:
        logger.info("💾 در حال ذخیره نسخه پشتیبان نهایی دیتابیس در فضای ابری قبل از خاموش شدن...")
        try:
            await backup_to_cloud()
        except Exception as e:
            logger.error(f"خطا در بکاپ نهایی: {e}")
        keep_alive_task.cancel()
        periodic_sync_task.cancel()
        scheduler_task.cancel()
        await web_runner.cleanup()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ربات متوقف شد.")
