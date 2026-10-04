# 🤖 ربات تلگرام محاسبه دنگ و مدیریت هزینه‌های مشترک (Dong Calculator Bot)

یک ربات کامل، مدرن و پرسرعت برای تلگرام با پایتون ۳ و کتابخانه **aiogram 3** جهت ثبت خرج‌های گروهی (سفر، هم‌خانه‌ای، کافه، پروژه‌ها و...)، تسهیم هزینه‌ها و محاسبه فرمول بهینه تسویه حساب بدهی‌ها.

---

## ✨ ویژگی‌ها و قابلیت‌های ربات

* **👥 مدیریت گروه‌ها و اعضا:**
  * امکان ساخت بی‌نهایت گروه دنگ (مثلاً: سفر شمال، خرید منزل، ناهار شرکت و...)
  * تولید **لینک دعوت اختصاصی (Deep Link)** برای هر گروه جهت عضویت آنی دوستان با یک کلیک
* **💸 ثبت هوشمند هزینه‌ها (FSM):**
  * دریافت عنوان هزینه (بابت چی خرج شده؟)
  * دریافت مبلغ به تومان با پشتیبانی از ارقام فارسی/انگلیسی، ویرگول و پسوندهای تومان، هزار (k) و میلیون (m)
  * انتخاب پرداخت‌کننده از بین اعضای گروه
  * تعیین افراد سهیم در دنگ (تقسیم مساوی بین همه با ۱ کلیک یا انتخاب چند نفر خاص)
* **📊 گزارش‌گیری شفاف:**
  * جمع کل مخارج دوره جاری
  * وضعیت تک‌تک اعضا (مبلغ کل پرداختی، سهم هزینه، وضعیت طلبکاری یا بدهکاری)
* **⚖️ الگوریتم هوشمند تسویه بدهی (Minimizing Transactions):**
  * مشخص کردن دقیق این‌که **چه کسی باید چقدر به چه کسی پرداخت کند** تا با **کمترین تعداد جابجایی پول** کل حساب‌ها صاف شوند.
* **🔄 صفر کردن حساب‌ها (بستن دوره مالی):**
  * امکان صفر کردن ترازها پس از واریز مبالغ توسط اعضا جهت شروع خریدهای دوره جدید
  * حفظ و نگهداری کامل تاریخچه هزینه‌های قبلی
* **📜 مشاهده تاریخچه و امکان حذف هزینه اشتباه**
* **🌐 پشتیبانی داخلی از پروکسی (SOCKS5/HTTP)** برای عبور از فیلترینگ در محیط توسعه ایران

---

## 🚀 راهنمای سریع راه‌اندازی (Step-by-Step)

### ۱. دریافت توکن ربات از تلگرام
1. در تلگرام وارد ربات **[@BotFather](https://t.me/BotFather)** شوید.
2. دستور `/newbot` را ارسال کنید.
3. یک نام نمایشی و سپس یک نام کاربری (که به `bot` ختم شود، مثل `MyDongCalculatorBot`) وارد کنید.
4. توکن داده شده (مانند `123456789:ABCdef...`) را کپی کنید.

### ۲. تنظیم توکن در پروژه
فایل [`.env`](file:///c:/Users/Puriya/OneDrive/Desktop/test/.env) را باز کنید و توکن خود را در متغیر `BOT_TOKEN` قرار دهید:

```env
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
```

> **نکته در صورت اجرای روی کامپیوتر شخصی در ایران:**  
> اگر فیلترشکن شما فعال است، می‌توانید پورت پروکسی محلی (مثلاً v2ray یا نکو‌ری) را نیز در `.env` وارد کنید:
> ```env
> PROXY_URL=socks5://127.0.0.1:10808
> ```

### ۳. نصب پیش‌نیازها
اگر در محیط جدیدی اجرا می‌کنید:
```bash
pip install -r requirements.txt
```

### ۴. اجرای ربات
کافی است دستور زیر را اجرا کنید:
```bash
python bot.py
```

---

## 🛠️ ساختار فایل‌های پروژه

* [`bot.py`](file:///c:/Users/Puriya/OneDrive/Desktop/test/bot.py): فایل اصلی اجرای ربات و کانفیگ پولینگ (Polling)
* [`database.py`](file:///c:/Users/Puriya/OneDrive/Desktop/test/database.py): لایه دیتابیس ناهمگام (Async SQLite با `aiosqlite`)
* [`calculator.py`](file:///c:/Users/Puriya/OneDrive/Desktop/test/calculator.py): الگوریتم محاسبه دنگ و بهینه‌سازی تسویه بدهی‌ها
* [`helpers.py`](file:///c:/Users/Puriya/OneDrive/Desktop/test/helpers.py): توابع کمکی تبدیل اعداد، فرمت مبالغ تومان و منشن کاربران
* [`keyboards.py`](file:///c:/Users/Puriya/OneDrive/Desktop/test/keyboards.py): دکمه‌های شیشه‌ای تعاملی و منوها
* [`states.py`](file:///c:/Users/Puriya/OneDrive/Desktop/test/states.py): استیت‌های ماشین حالت (FSM)
* [`handlers/`](file:///c:/Users/Puriya/OneDrive/Desktop/test/handlers):
  * `start.py`: دستور استارت، عضویت با لینک دعوت، منوی راهنما
  * `groups.py`: ساخت گروه، لیست گروه‌ها، مشاهده اعضا و دریافت لینک دعوت
  * `expenses.py`: سناریوی ثبت قدم به قدم خرج، انتخاب پرداخت‌کننده و سهیم‌ها
  * `reports.py`: گزارش بدهی/طلب، فرمول نهایی تسویه، صفر کردن حساب‌ها
* [`test_logic.py`](file:///c:/Users/Puriya/OneDrive/Desktop/test/test_logic.py): تست خودکار جامع صحت عملکرد الگوریتم و دیتابیس

---

## ☁️ استقرار روی سرور (Deploy روی VPS لینوکس)

برای اجرای دائمی و ۲۴ ساعته روی سرور اوبونتو:

۱. فایل‌ها را روی سرور منتقل کنید.  
۲. یک سرویس systemd بسازید:
```bash
sudo nano /etc/systemd/system/dongbot.service
```

محتوای زیر را قرار دهید:
```ini
[Unit]
Description=Telegram Dong Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/dong_bot
ExecStart=/usr/bin/python3 /root/dong_bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

۳. فعال‌سازی و راه‌اندازی سرویس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable dongbot
sudo systemctl start dongbot
```
