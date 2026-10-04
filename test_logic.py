import asyncio
import os
import sys

# تنظیم خروجی کنسول روی UTF-8 برای ویندوز
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import database as db
from calculator import calculate_group_balances
from helpers import clean_amount_input, format_amount
from bank_utils import clean_card_input, format_card_number, detect_bank_name
import tones

async def test_full_pipeline():
    print("--- ۱. تست پاکسازی و تحلیل ورودی‌ها و کارت بانکی ---")
    assert clean_amount_input("450,000") == 450000
    assert clean_amount_input("۴۵۰,۰۰۰") == 450000
    assert clean_amount_input("250k") == 250000
    assert clean_amount_input("50 هزار تومان") == 50000
    
    # تست کارت بانکی
    raw_card = "۶۰۳۷-۹۹۷۵-۱۲۳۴-۵۶۷۸"
    cleaned = clean_card_input(raw_card)
    assert cleaned == "6037997512345678"
    assert format_card_number(cleaned) == "6037-9975-1234-5678"
    assert detect_bank_name(cleaned) == "بانک ملی"
    print("✅ تست مبالغ و اعتبارسنجی کارت بانکی پاس شد.")

    # تست ایمن‌سازی کاراکترهای خاص HTML
    from helpers import safe
    assert safe("پیتزا <مخصوص> & نوشابه") == "پیتزا &lt;مخصوص&gt; &amp; نوشابه"
    assert safe("Ali <3") == "Ali &lt;3"
    assert safe(None) == ""
    print("✅ تست ایمن‌سازی و فیلتر کاراکترهای خاص HTML پاس شد.")

    print("\n--- ۲. تست تغییر لحن‌ها (رسمی، دوستانه، بی‌ادب) ---")
    for t_name in ["formal", "friendly", "toxic"]:
        dash = tones.msg_group_dashboard(t_name, "تست", 3, "اعضا", 100000, 1, "لحن")
        prompt_t = tones.msg_expense_title_prompt(t_name)
        prompt_a = tones.msg_expense_amount_prompt(t_name, "غذا")
        prompt_p = tones.msg_expense_payer_prompt(t_name, "غذا", "100,000")
        prompt_s = tones.msg_expense_shares_prompt(t_name, "غذا", "100,000", "علی")
        saved = tones.msg_expense_saved(t_name, "غذا", "100,000", "علی", 2, "50,000", "رضا")
        remind = tones.render_reminder_msg(t_name, "طلبکار", "بدهکار", 50000, "کارت: 6037")
        notice = tones.render_payment_notice(t_name, "بدهکار", "طلبکار", 50000)
        no_exp = tones.render_no_expenses_msg(t_name, "تست")
        all_set = tones.render_all_settled_msg(t_name, "تست")
        zero_c = tones.msg_zero_confirm(t_name, "تست")
        zero_d = tones.msg_zero_done(t_name, "تست", 2)
        food_intro_empty = tones.msg_food_picker_intro(t_name, "تست", [])
        food_intro_items = tones.msg_food_picker_intro(t_name, "تست", ["پیتزا", "کباب"])
        food_win = tones.msg_food_winner(t_name, "تست", "پیتزا", 2)
        assert len(dash) > 0 and len(prompt_t) > 0 and len(saved) > 0
        assert len(food_intro_empty) > 0 and len(food_win) > 0
    print("✅ تمامی پیام‌های ۳ گانه لحن و انتخاب غذا با موفقیت ارزیابی شدند.")

    print("\n--- ۳. تست دیتابیس و تراکنش‌ها ---")
    import cloud_db_sync
    async def dummy_coro(*args, **kwargs):
        pass
    cloud_db_sync.backup_to_cloud = dummy_coro
    cloud_db_sync.restore_from_cloud = dummy_coro

    db.DB_PATH = "test_dong.db"
    if os.path.exists("test_dong.db"):
        os.remove("test_dong.db")
        
    await db.init_db()
    
    # ثبت ۳ کاربر
    await db.upsert_user(101, "ali_dev", "علی رضایی")
    await db.upsert_user(102, "reza_m", "رضا محمدی")
    await db.upsert_user(103, "sara_k", "سارا کریمی")
    
    # ساخت گروه توسط علی
    group_id, invite_code = await db.create_group("سفر شمال 🌊", 101)
    assert group_id > 0
    assert len(invite_code) == 8
    
    # تست دریافت گروه‌های کاربر (بررسی عدم پاک شدن گروه)
    user_groups = await db.get_user_groups(101)
    assert len(user_groups) == 1
    assert user_groups[0]["id"] == group_id
    print("✅ تست نمایش لیست گروه‌ها بعد از ایجاد با موفقیت پاس شد.")
    
    # تغییر لحن گروه به بی‌ادب و سپس دوستانه
    await db.set_group_tone(group_id, "toxic")
    assert (await db.get_group_tone(group_id)) == "toxic"
    await db.set_group_tone(group_id, "friendly")
    assert (await db.get_group_tone(group_id)) == "friendly"
    print("✅ تست تنظیم و فراخوانی لحن گروه پاس شد.")

    # عضویت رضا و سارا
    await db.add_group_member(group_id, 102)
    await db.add_group_member(group_id, 103)
    
    members = await db.get_group_members(group_id)
    assert len(members) == 3
    print(f"✅ گروه «سفر شمال» با {len(members)} عضو ایجاد شد.")

    # ثبت کارت بانکی برای علی
    c1_id, is_new1 = await db.add_user_card(101, "6037997512345678", "بانک ملی")
    assert is_new1 is True
    # افزودن کارت دوم برای علی (بلو بانک)
    c2_id, is_new2 = await db.add_user_card(101, "6219861234567890", "بلو بانک")
    assert is_new2 is True
    
    ali_cards = await db.get_user_cards(101)
    assert len(ali_cards) == 2
    assert ali_cards[0]["is_default"] == 1  # کارت اول پیش‌فرض است
    
    # تغییر کارت پیش‌فرض به بلو بانک
    await db.set_default_card(101, c2_id)
    ali_cards_updated = await db.get_user_cards(101)
    assert ali_cards_updated[0]["card_number"] == "6219861234567890"
    assert ali_cards_updated[0]["is_default"] == 1
    
    card_info = await db.get_user_card(101)
    assert card_info["card_number"] == "6219861234567890"
    assert card_info["bank_name"] == "بلو بانک"
    print("✅ تست ثبت چند شماره کارت، تفکیک کارت‌ها و تغییر کارت اصلی پیش‌فرض پاس شد.")

    # سناریو ۱: علی ۳۰۰,۰۰۰ تومان بابت شام (تقسیم مساوی بین ۳ نفر: هر نفر ۱۰۰ هزار)
    shares1 = {101: 100000, 102: 100000, 103: 100000}
    exp1 = await db.add_expense(group_id, 101, "شام رستوران", 300000, shares1)
    assert exp1 > 0

    # سناریو ۲: رضا ۱۵۰,۰۰۰ تومان بابت بنزین (فقط بین رضا و علی: هر نفر ۷۵ هزار)
    shares2 = {101: 75000, 102: 75000}
    exp2 = await db.add_expense(group_id, 102, "بنزین", 150000, shares2)
    assert exp2 > 0

    # بررسی ترازها
    active_expenses = await db.get_active_expenses(group_id)
    assert len(active_expenses) == 2
    
    calc_res = calculate_group_balances(members, active_expenses)
    total_spent = calc_res["total_spent"]
    assert total_spent == 450000
    
    stats = {s["user"]["id"]: s for s in calc_res["member_stats"]}
    assert stats[101]["net"] == 125000  # طلبکار
    assert stats[102]["net"] == -25000  # بدهکار
    assert stats[103]["net"] == -100000 # بدهکار

    settlements = calc_res["settlements"]
    assert len(settlements) == 2
    assert settlements[0]["amount"] + settlements[1]["amount"] == 125000
    print("✅ الگوریتم محاسبه دنگ و تسویه دقیقاً درست عمل کرد.")

    # تست حذف عضو توسط سرگروه
    removed = await db.remove_group_member(group_id, 103)
    assert removed is True
    members_after_kick = await db.get_group_members(group_id)
    assert len(members_after_kick) == 2
    print("✅ تست اخراج عضو توسط سرگروه پاس شد.")

    print("\n--- ۴. تست صفر کردن حساب‌ها ---")
    settled_count = await db.settle_group(group_id)
    assert settled_count == 2
    
    active_after = await db.get_active_expenses(group_id)
    assert len(active_after) == 0
    
    history = await db.get_group_history(group_id)
    assert len(history) == 2
    print("✅ تاریخچه هزینه‌ها پس از صفر کردن حساب به درستی حفظ شد.")

    # تست دریافت تمام کاربران
    all_users = await db.get_all_user_ids()
    assert len(all_users) >= 3
    # تست غیرفعال‌سازی کاربر بلاک‌کننده و حذف از لیست برودکست
    await db.mark_user_inactive(103)
    active_users = await db.get_all_user_ids()
    assert 103 not in active_users
    await db.mark_user_active(103)
    active_users_restored = await db.get_all_user_ids()
    assert 103 in active_users_restored
    print("✅ تست دریافت لیست کاربران و فیلتر هوشمند کاربران غیرفعال پاس شد.")

    # تست سیستم پیام‌های انگیزشی کافه‌ای و عدم تکرار
    import motivational
    quote_idx1, quote1 = await motivational.get_daily_quote_unique()
    assert len(quote1) > 10
    await db.log_sent_quote(quote_idx1, "2026-10-04")
    
    quote_idx2, quote2 = await motivational.get_daily_quote_unique()
    assert quote_idx1 != quote_idx2  # تضمین عدم تکرار جمله متوالی
    
    msg_q = motivational.format_cafe_quote_message(quote1)
    assert "کافه دنگ" in msg_q
    print("✅ تست قالب، متن‌های کافه‌ای و الگوریتم عدم تکرار جملات ۹ صبح پاس شد.")

    # تست باطل کردن و ساخت مجدد لینک دعوت توسط سرگروه
    old_group = await db.get_group_by_id(group_id)
    old_code = old_group["invite_code"]
    non_creator_regen = await db.regenerate_invite_code(group_id, 102)
    assert non_creator_regen is None  # فقط سرگروه مجاز است
    new_code = await db.regenerate_invite_code(group_id, 101)
    assert new_code is not None and new_code != old_code
    group_by_old = await db.get_group_by_code(old_code)
    assert group_by_old is None  # لینک قدیمی باطل شده
    group_by_new = await db.get_group_by_code(new_code)
    assert group_by_new["id"] == group_id
    print("✅ تست ابطال لینک قبلی و تولید لینک دعوت جدید توسط سرگروه پاس شد.")

    # تست تشخیص هوشمندانه نام معنادار و پرسش در صورت عدم وجود
    from name_utils import guess_meaningful_name, clean_input_name, is_clean_persian_name
    assert guess_meaningful_name("poriA", "Eazi", "Airoq77") == "پوریا"
    assert guess_meaningful_name("poriA Eazi") == "پوریا"
    assert guess_meaningful_name("پوریا ایزی", None, "poriaiziy") == "پوریا"
    assert guess_meaningful_name("Ali Rezaei") == "علی"
    assert guess_meaningful_name("Dr. Mohammad") == "محمد"
    assert guess_meaningful_name("👑 Sara 👑") == "سارا"
    assert guess_meaningful_name("꧁༺عسل༻꧂") == "عسل"
    assert guess_meaningful_name("امیر حسین") == "امیر حسین"
    assert guess_meaningful_name("...", None, "xyz99") is None  # باید از کاربر بپرسد
    assert guess_meaningful_name("🥀💔") is None  # باید از کاربر بپرسد
    assert clean_input_name(" سهراب ") == "سهراب"
    assert clean_input_name("!!") is None
    assert is_clean_persian_name("پوریا") is True
    assert is_clean_persian_name("poriA Eazi") is False

    # تست ذخیره، ارتقای خودکار و دریافت نام صدا زدن در دیتابیس
    await db.set_user_calling_name(101, "علی")
    assert (await db.get_user_calling_name(101)) == "علی"
    
    # تست ارتقای خودکار کاربری که نام قبلی‌اش خام بوده (مانند poriA Eazi)
    await db.upsert_user(999, "Airoq77", "poriA Eazi")
    # نام باید به طور خودکار به پوریا تبدیل شود
    upgraded_name = await db.get_user_calling_name(999)
    assert upgraded_name == "پوریا"
    print("✅ تست تشخیص هوشمند نام پروفایل و اعتبارسنجی نام دستی پاس شد.")

    # تست حذف کامل گروه توسط سازنده
    non_creator_del = await db.delete_group(group_id, 102)
    assert non_creator_del is False  # کاربر غیرسازنده نمی‌تواند گروه را حذف کند
    creator_del = await db.delete_group(group_id, 101)
    assert creator_del is True
    groups_after_del = await db.get_user_groups(101)
    assert len(groups_after_del) == 0
    print("✅ تست حذف کامل گروه توسط سازنده پاس شد.")

    # تست دیتابیس اسامی رندوم گروه (حداقل ۵۰۰ اسم، بدون تکرار، از ۲ تا ۵ کلمه)
    from random_names import FUNNY_GROUP_NAMES, get_random_group_name
    assert len(FUNNY_GROUP_NAMES) >= 500, f"Expected >= 500 names, got {len(FUNNY_GROUP_NAMES)}"
    assert len(set(FUNNY_GROUP_NAMES)) == len(FUNNY_GROUP_NAMES), "Duplicate names found in FUNNY_GROUP_NAMES!"
    
    import re
    for name in FUNNY_GROUP_NAMES:
        # پاکسازی اموجی و علائم برای شمارش کلمات
        text_only = name.rsplit(" ", 1)[0] if any(ord(c) > 127 for c in name.rsplit(" ", 1)[-1]) and len(name.rsplit(" ", 1)[-1]) <= 4 else name
        cleaned = re.sub(r'[^\w\s\u200c]', ' ', text_only)
        words = [w for w in cleaned.split() if w.strip() and not w.isdigit()]
        wc = len(words)
        assert 2 <= wc <= 5, f"Name '{name}' has invalid word count {wc}!"
        
    sampled_name = get_random_group_name()
    assert isinstance(sampled_name, str) and len(sampled_name) > 0
    print(f"✅ تست صحت، تنوع و شمارش کلمات اسامی رندوم گروه ({len(FUNNY_GROUP_NAMES)} اسم از ۲ تا ۵ کلمه‌ای بدون تکرار) پاس شد.")

    if os.path.exists("test_dong.db"):
        os.remove("test_dong.db")
    print("\n🎉 تمامی تست‌های عملکردی سیستم با موفقیت ۱۰۰٪ پاس شدند!")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
