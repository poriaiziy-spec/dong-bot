import os
import asyncio
import datetime
import logging
import aiohttp
import aiosqlite
from aiogram import Bot
from config import ADMIN_IDS, WEB_APP_URL, DB_PATH, BOT_TOKEN
from cloud_db_sync import _last_backup_status, GITHUB_TOKEN
import database as db

logger = logging.getLogger(__name__)

# کل سهمیه هاست رایگان ماهانه در پلتفرم‌هایی مانند رندر (۷۵۰ ساعت)
TOTAL_FREE_HOURS = 750.0

# متغیرهای وضعیت نظارت بر پاسخگویی سرور وب
_web_failure_count = 0
_web_is_down_alerted = False
_last_check_status = "در حال بررسی"
_last_check_error = None
_last_response_time_ms = 0
_last_check_time = None


def get_current_month_key() -> str:
    """دریافت کلید ماه جاری میلادی (مثلاً: 2026-10)"""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")


def make_progress_bar(percent: float, total_blocks: int = 10) -> str:
    """تولید نوار پیشرفت متنی زیبا"""
    filled = min(total_blocks, max(0, int(round((percent / 100.0) * total_blocks))))
    empty = total_blocks - filled
    return "█" * filled + "░" * empty


async def check_web_health() -> tuple[bool, str | None, int]:
    """
    بررسی پاسخگویی سرور وب و مینی‌اپ با ارسال درخواست به روت /health
    """
    global _last_check_status, _last_check_error, _last_response_time_ms, _last_check_time
    target_url = f"{WEB_APP_URL.rstrip('/')}/health"
    start_time = datetime.datetime.now()
    _last_check_time = start_time.strftime("%H:%M:%S")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(target_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                elapsed_ms = int((datetime.datetime.now() - start_time).total_seconds() * 1000)
                _last_response_time_ms = elapsed_ms
                if resp.status == 200:
                    _last_check_status = "آنلاین و پاسخگو ✅"
                    _last_check_error = None
                    return True, None, elapsed_ms
                else:
                    err_msg = f"کد خطا HTTP {resp.status}"
                    _last_check_status = f"خطای {resp.status} ⚠️"
                    _last_check_error = err_msg
                    return False, err_msg, elapsed_ms
    except asyncio.TimeoutError:
        _last_check_status = "عدم پاسخ (Timeout) ⏱️"
        _last_check_error = "عدم دریافت پاسخ در مهلت ۱۵ ثانیه"
        _last_response_time_ms = 15000
        return False, _last_check_error, 15000
    except Exception as e:
        err_msg = str(e)
        _last_check_status = "قطع ارتباط ❌"
        _last_check_error = err_msg
        _last_response_time_ms = 0
        return False, err_msg, 0


async def notify_admins(bot: Bot, text: str):
    """ارسال اعلان یا هشدار به تمام مدیران ربات"""
    if not ADMIN_IDS:
        return
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"عدم امکان ارسال هشدار سرور به ادمین {admin_id}: {e}")


async def get_server_status_data() -> dict:
    """جمع‌آوری کامل داده‌های سلامت سرور، مصرف ساعات هاست و دیتابیس"""
    month_key = get_current_month_key()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    # آمار دیتابیس از زمان فعالیت واقعی سرور
    stats = await db.get_server_uptime_stats(month_key)
    active_hours = stats["active_hours"]

    # همچنین محاسبه ساعات سپری‌شده از تقویم ماه جاری (حالت ۲۴/۷ مداوم)
    start_of_month = datetime.datetime(now_utc.year, now_utc.month, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    calendar_hours = (now_utc - start_of_month).total_seconds() / 3600.0

    # استفاده از بیشترین مقدار بین زمان واقعی ثبت‌شده و زمان تقویمی ماه جاری
    effective_hours = min(TOTAL_FREE_HOURS, max(active_hours, calendar_hours))
    percent_used = min(100.0, (effective_hours / TOTAL_FREE_HOURS) * 100.0)
    remaining_hours = max(0.0, TOTAL_FREE_HOURS - effective_hours)
    remaining_days = remaining_hours / 24.0

    # آمار دیتابیس
    db_counts = {}
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            for tbl in ["users", "groups", "expenses", "shopping_items", "user_cards"]:
                try:
                    async with conn.execute(f"SELECT COUNT(*) FROM {tbl}") as cur:
                        row = await cur.fetchone()
                        db_counts[tbl] = row[0] if row else 0
                except Exception:
                    db_counts[tbl] = 0
    except Exception:
        pass

    return {
        "month_key": month_key,
        "month_name": now_utc.strftime("%B %Y"),
        "active_hours": effective_hours,
        "total_free_hours": TOTAL_FREE_HOURS,
        "percent_used": percent_used,
        "remaining_hours": remaining_hours,
        "remaining_days": remaining_days,
        "last_warning_level": stats["last_warning_level"],
        "web_status": _last_check_status,
        "web_error": _last_check_error,
        "response_time_ms": _last_response_time_ms,
        "last_check_time": _last_check_time,
        "db_counts": db_counts,
        "cloud_backup_status": _last_backup_status,
        "web_app_url": WEB_APP_URL
    }


def format_server_status_text(data: dict) -> str:
    """تولید گزارش متنی زیبا و فرمت‌شده از وضعیت سرور و سهمیه هاست رایگان"""
    percent = data["percent_used"]
    prog_bar = make_progress_bar(percent, total_blocks=10)

    # رنگ و آیکون مصرف
    if percent >= 90:
        usage_badge = "🔴 بحرانی (رو به اتمام)"
    elif percent >= 75:
        usage_badge = "🟠 هشدار (بیش از ۷۵٪)"
    elif percent >= 50:
        usage_badge = "🟡 متوسط (بیش از ۵۰٪)"
    else:
        usage_badge = "🟢 عادی و امن"

    cloud_status_text = "ثبت شده و امن ✅" if data["cloud_backup_status"] else "در حال همگام‌سازی ⏳"

    text = (
        "📊 <b>گزارش پایش وضعیت سرور و سهمیه رایگان رندر:</b> ☕\n\n"
        f"🤖 <b>وضعیت بات تلگرام:</b> ۲۴/۷ آنلاین و فعال ✅\n"
        f"🌐 <b>وضعیت سرور وب:</b> {data['web_status']}\n"
        f"⚡ <b>سرعت پاسخگویی:</b> <code>{data['response_time_ms']} ms</code>\n"
        f"🔗 <b>آدرس وب‌اپ:</b> <code>{data['web_app_url']}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱️ <b>سهمیه هاست رایگان ماه ({data['month_name']}):</b>\n"
        f"• وضعیت مصرف: <b>{usage_badge}</b>\n"
        f"• ساعات مصرف‌شده: <b>{data['active_hours']:.1f}</b> از {int(data['total_free_hours'])} ساعت\n"
        f"• درصد مصرف سهمیه: <b>{percent:.1f}٪</b>\n"
        f"• زمان باقی‌مانده: <b>{data['remaining_hours']:.1f} ساعت</b> (~<b>{data['remaining_days']:.1f} روز</b>)\n"
        f"• پیشرفت: <code>[{prog_bar}] {percent:.1f}%</code>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "💾 <b>وضعیت دیتابیس و داده‌ها:</b>\n"
        f"• دورهمی‌های فعال: <b>{data['db_counts'].get('groups', 0)}</b>\n"
        f"• کل کاربران ثبت‌شده: <b>{data['db_counts'].get('users', 0)}</b>\n"
        f"• کل هزینه‌های ثبت‌شده: <b>{data['db_counts'].get('expenses', 0)}</b>\n"
        f"• اقلام لیست خرید: <b>{data['db_counts'].get('shopping_items', 0)}</b>\n"
        f"• پشتیبان‌گیری ابری کلاد: <b>{cloud_status_text}</b>\n\n"
        f"<i>🕒 آخرین بررسی: {data['last_check_time'] or 'هم‌اکنون'}</i>"
    )
    return text


async def start_server_monitor_task(bot: Bot):
    """
    تسک پس‌زمینه پایش مداوم (Watchdog):
    ۱. ثبت زمان فعالیت ساعتی و بررسی سهمیه هاست رایگان (۷۰٪، ۸۵٪، ۹۵٪)
    ۲. بررسی زنده بودن و پاسخگویی سرور وب و اعلام فوری در صورت بروز اختلال
    """
    global _web_failure_count, _web_is_down_alerted

    # تاخیر اولیه جهت لود کامل سرور وب و ربات
    await asyncio.sleep(25)
    logger.info("🛡️ تسک پایش سلامت سرور و هشدار سهمیه رایگان فعال شد.")

    while True:
        try:
            month_key = get_current_month_key()

            # ۱. ثبت ۱ دقیقه فعالیت در دیتابیس
            active_hours, last_warn = await db.record_server_uptime_minute(month_key, seconds=60)

            # محاسبه درصد مصرف کل ماه جاری
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            start_of_month = datetime.datetime(now_utc.year, now_utc.month, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
            calendar_hours = (now_utc - start_of_month).total_seconds() / 3600.0
            effective_hours = min(TOTAL_FREE_HOURS, max(active_hours, calendar_hours))
            percent = (effective_hours / TOTAL_FREE_HOURS) * 100.0
            remaining_hours = max(0.0, TOTAL_FREE_HOURS - effective_hours)
            remaining_days = remaining_hours / 24.0

            # بررسی سطوح هشدار ساعات هاست رایگان
            if percent >= 95.0 and last_warn < 95:
                await db.update_server_warning_level(month_key, 95)
                warn_text = (
                    "🚨 <b>هشدار اضطراری ادمین: سهمیه هاست رایگان رو به اتمام است! (بیش از ۹۵٪)</b> 🔴\n\n"
                    f"ادمین عزیز، ربات تاکنون حدود <b>{effective_hours:.1f} ساعت</b> از سقف ۷۵۰ ساعت ماه جاری رندر را مصرف کرده است.\n"
                    f"⏳ <b>تنها حدود {remaining_hours:.1f} ساعت (~{remaining_days:.1f} روز)</b> تا اتمام کامل سهمیه و خاموشی سرور باقی مانده است!\n\n"
                    "💡 <b>اقدام پیشنهادی:</b> لطفاً برای جلوگیری از قطعی، پیش از خاموش شدن نسبت به انتقال به اکانت جدید یا تهیه سرور اقدام فرمایید."
                )
                await notify_admins(bot, warn_text)

            elif percent >= 85.0 and last_warn < 85:
                await db.update_server_warning_level(month_key, 85)
                warn_text = (
                    "🟠 <b>هشدار جدی ادمین: ۸۵٪ از ساعات رایگان ماه مصرف شد!</b>\n\n"
                    f"ادمین عزیز، مصرف ماهانه ربات به <b>{effective_hours:.1f} ساعت</b> رسیده است.\n"
                    f"⏳ سهمیه باقی‌مانده: حدود <b>{remaining_hours:.1f} ساعت (~{remaining_days:.1f} روز)</b>.\n"
                    "💡 تا اتمام ماه میلادی جاری دقت داشته باشید که به زودی به سقف رایگان نزدیک می‌شویم."
                )
                await notify_admins(bot, warn_text)

            elif percent >= 70.0 and last_warn < 70:
                await db.update_server_warning_level(month_key, 70)
                warn_text = (
                    "⚠️ <b>اطلاعیه مصرف سهمیه هاست (سطح ۷۰٪):</b>\n\n"
                    f"ادمین عزیز، ربات تاکنون <b>{effective_hours:.1f} ساعت</b> از ۷۵۰ ساعت رایگان ماه را مصرف کرده است.\n"
                    f"⏳ سهمیه باقی‌مانده: <b>{remaining_hours:.1f} ساعت (~{remaining_days:.1f} روز)</b>.\n"
                    "وضعیت در حال حاضر پایدار و عادی است."
                )
                await notify_admins(bot, warn_text)

            # ۲. بررسی پاسخگویی سرور وب (Web Health Check)
            is_ok, err_msg, ms = await check_web_health()

            if not is_ok:
                _web_failure_count += 1
                logger.warning(f"⚠️ خطای پایش وب‌سرور (شمارش: {_web_failure_count}): {err_msg}")

                # اگر ۳ بار متوالی (حدود ۳ دقیقه) سرور وب پاسخ نداد و قبلاً هشدار داده نشده
                if _web_failure_count >= 3 and not _web_is_down_alerted:
                    _web_is_down_alerted = True
                    alert_msg = (
                        "🚨 <b>هشدار مهم: عدم پاسخگویی سرور وب! (Server Not Responding)</b> ⚠️\n\n"
                        f"سرور وب و مینی‌اپ در آدرس زیر بیش از ۳ دقیقه است که پاسخ نمی‌دهد:\n"
                        f"🌐 <code>{WEB_APP_URL}</code>\n\n"
                        f"❌ <b>خطای مشاهده‌شده:</b> <code>{err_msg}</code>\n\n"
                        "💡 لطفاً داشبورد رندر را باز کرده و لاگ‌ها یا وضعیت سرویس را بررسی کنید."
                    )
                    await notify_admins(bot, alert_msg)
            else:
                # اگر سرور قبلاً خطا داده بود و الان دوباره آنلاین شد
                if _web_is_down_alerted:
                    _web_is_down_alerted = False
                    _web_failure_count = 0
                    recovery_msg = (
                        "✅ <b>اطلاعیه رفع اختلال: پاسخگویی سرور وب به وضعیت عادی بازگشت!</b> 🌸\n\n"
                        f"🌐 آدرس: <code>{WEB_APP_URL}</code>\n"
                        f"⚡ زمان پاسخگویی: <b>{ms} میلی‌ثانیه</b>\n"
                        "ربات و مینی‌اپ بدون مشکل در حال فعالیت هستند."
                    )
                    await notify_admins(bot, recovery_msg)
                else:
                    _web_failure_count = 0

        except Exception as e:
            logger.error(f"خطا در تسک پایش سرور: {e}", exc_info=True)

        # اجرای بررسی هر ۶۰ ثانیه
        await asyncio.sleep(60)
