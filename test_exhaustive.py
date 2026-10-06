# -*- coding: utf-8 -*-
"""
جامع‌ترین تست شرایط خاص، محاسبات ریاضی، دیتابیس و امنیت ربات کافه دنگ
پوشش ۱۰۰٪ تمام سناریوهای بحرانی و شرایط غیرعادی
"""
import asyncio
import os
import sys

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import database as db
import keyboards as kb
from calculator import calculate_group_balances
from helpers import clean_amount_input, format_amount, safe, mention_user
from bank_utils import clean_card_input, format_card_number, detect_bank_name
import tones
from random_names import FUNNY_GROUP_NAMES, get_random_group_name, get_random_member_nickname

async def test_all_scenarios():
    print("=" * 60)
    print("🚀 شروع اجرای آزمون جامع شرایط مختلف (Exhaustive Bot Test Suite)")
    print("=" * 60)

    # -------------------------------------------------------------
    # سناریو ۱: تست مبالغ و ورودی‌های نامعتبر / خاص
    # -------------------------------------------------------------
    print("\n--- [بخش ۱] آزمون جامع پاکسازی و اعتبارسنجی ورودی مبالغ ---")
    # مبالغ منفی یا صفر باید بلافاصله رد شوند
    assert clean_amount_input("-1000") is None, "Negative amount should be None"
    assert clean_amount_input("-50k") is None, "Negative k-amount should be None"
    assert clean_amount_input("0") is None, "Zero amount should be None"
    assert clean_amount_input("0 تومان") is None, "Zero with currency should be None"
    assert clean_amount_input(None) is None, "None input should be None"
    assert clean_amount_input("") is None, "Empty string should be None"
    assert clean_amount_input("سلام خوبی") is None, "Pure text should be None"
    assert clean_amount_input("!@#$%^&*") is None, "Symbols should be None"

    # مبالغ اعشاری با ضریب
    assert clean_amount_input("2.5k") == 2500, "2.5k should be 2500"
    assert clean_amount_input("1.5m") == 1500000, "1.5m should be 1500000"
    assert clean_amount_input("۲.۵ میلیون") == 2500000, "Persian 2.5 million should be 2500000"
    assert clean_amount_input("۰.۵ میلیون") == 500000, "Persian 0.5 million should be 500000"
    assert clean_amount_input("۱.۲ هزار تومان") == 1200, "Persian 1.2 thousand should be 1200"

    # فرمت‌های استاندارد
    assert clean_amount_input("1,250,000 تومان") == 1250000
    assert clean_amount_input("۵۰۰ هزار") == 500000
    assert clean_amount_input("500k") == 500000
    print("✅ تمامی تست‌های ورودی مبلغ (شامل اعداد منفی، اعشاری، ضرایب k/m و کاراکترهای عجیب) پاس شدند.")

    # -------------------------------------------------------------
    # سناریو ۲: تست شماره کارت بانکی در شرایط غیرعادی
    # -------------------------------------------------------------
    print("\n--- [بخش ۲] آزمون جامع کارت‌های بانکی و پیش‌شماره‌ها ---")
    assert clean_card_input(None) is None
    assert clean_card_input("") is None
    assert clean_card_input("123456") is None  # کمتر از ۱۶ رقم
    assert clean_card_input("603799112233445566") is None  # بیشتر از ۱۶ رقم
    assert clean_card_input("abcd-efgh-ijkl-mnop") is None
    
    # تست تبدیل ارقام فارسی و جداکننده‌ها
    raw_persian = "۶۰۳۷ ۹۹۷۵ ۱۲۳۴ ۵۶۷۸"
    assert clean_card_input(raw_persian) == "6037997512345678"
    assert format_card_number(None) == "ثبت نشده"
    assert format_card_number("6037997512345678") == "6037-9975-1234-5678"
    
    # تست تشخیص بانک
    assert detect_bank_name("6037991122334455") == "بانک ملی"
    assert detect_bank_name("6219861122334455") == "بانک سامان"
    assert detect_bank_name("6063731122334455") == "بلو بانک (Blu) / مهر ایران"
    assert detect_bank_name("9999991122334455") is None  # بانک ناشناخته
    assert detect_bank_name(None) is None
    print("✅ تمامی تست‌های اعتبارسنجی و تشخیص شماره کارت بانکی پاس شدند.")

    # -------------------------------------------------------------
    # سناریو ۳: تست ایمنی HTML و کاراکترهای خطرناک
    # -------------------------------------------------------------
    print("\n--- [بخش ۳] آزمون ایمنی HTML و عدم تداخل قالب تلگرام ---")
    dangerous_text = "<script>alert('xss')</script> & <b>bold</b>"
    escaped = safe(dangerous_text)
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped
    assert "&amp;" in escaped

    # منشن تلگرام با کاراکتر & و علائم ریاضی
    m_html = mention_user(123456, "Ali & Sara <3>", "ali_user")
    assert "&amp;" in m_html
    assert "&lt;3&gt;" in m_html
    assert '<a href="https://t.me/ali_user">' in m_html
    print("✅ تمامی آزمون‌های فیلتر و ضدتزریق HTML با موفقیت پاس شدند.")

    # -------------------------------------------------------------
    # سناریو ۴: الگوریتم ریاضی محاسبه دنگ در شرایط خاص
    # -------------------------------------------------------------
    print("\n--- [بخش ۴] آزمون ریاضیات، تسهیم نابرابر و تسویه بدهی ---")
    
    # ۱. حالت بدون هیچ هزینه‌ای
    members_3 = [
        {"id": 1, "full_name": "علی"},
        {"id": 2, "full_name": "رضا"},
        {"id": 3, "full_name": "سارا"}
    ]
    res_empty = calculate_group_balances(members_3, [])
    assert res_empty["total_spent"] == 0
    assert len(res_empty["settlements"]) == 0
    for s in res_empty["member_stats"]:
        assert s["net"] == 0

    # ۲. تقسیم نابرابر ۱۰۰,۰۰۰ تومان بین ۳ نفر (باقیمانده به نفر اول اضافه می‌شود)
    # ۱۰۰,۰۰۰ // ۳ = ۳۳,۳۳۳ و باقیمانده ۱ => ۳۳,۳۳۴ + ۳۳,۳۳۳ + ۳۳,۳۳۳ = ۱۰۰,۰۰۰
    exp_uneven = [{
        "payer_id": 1,
        "amount": 100000,
        "shares": [
            {"user_id": 1, "share_amount": 33334},
            {"user_id": 2, "share_amount": 33333},
            {"user_id": 3, "share_amount": 33333}
        ]
    }]
    res_uneven = calculate_group_balances(members_3, exp_uneven)
    assert res_uneven["total_spent"] == 100000
    stats_map = {s["user"]["id"]: s["net"] for s in res_uneven["member_stats"]}
    assert stats_map[1] == 66666   # طلبکار
    assert stats_map[2] == -33333  # بدهکار
    assert stats_map[3] == -33333  # بدهکار
    settle_sum = sum(st["amount"] for st in res_uneven["settlements"])
    assert settle_sum == 66666
    assert len(res_uneven["settlements"]) == 2

    # ۳. تسویه دوری (Circular Debt):
    # علی ۶۰ هزار برای رضا داد، رضا ۶۰ هزار برای سارا داد، سارا ۶۰ هزار برای علی داد
    # نتیجه نهایی: همه باید بی‌حساب (۰) باشند و هیچ تراکنشی نباید لازم باشد!
    exp_circular = [
        {"payer_id": 1, "amount": 60000, "shares": [{"user_id": 2, "share_amount": 60000}]},
        {"payer_id": 2, "amount": 60000, "shares": [{"user_id": 3, "share_amount": 60000}]},
        {"payer_id": 3, "amount": 60000, "shares": [{"user_id": 1, "share_amount": 60000}]}
    ]
    res_circular = calculate_group_balances(members_3, exp_circular)
    assert res_circular["total_spent"] == 180000
    for s in res_circular["member_stats"]:
        assert s["net"] == 0, f"User {s['user']['id']} net balance should be 0, got {s['net']}"
    assert len(res_circular["settlements"]) == 0, "Circular debts should yield 0 settlement transactions!"

    # ۴. عضو سابق (کاربری که از گروه رفته اما در خرج قبلی سهم داشته):
    exp_former = [
        {"payer_id": 1, "amount": 50000, "shares": [{"user_id": 999, "share_amount": 50000}]} # 999 در لیست اعضا نیست
    ]
    res_former = calculate_group_balances(members_3, exp_former)
    uids_in_stats = [s["user"]["id"] for s in res_former["member_stats"]]
    assert 999 in uids_in_stats
    assert len(uids_in_stats) == len(set(uids_in_stats)), "Duplicate user ID in stats!"
    former_stat = next(s for s in res_former["member_stats"] if s["user"]["id"] == 999)
    assert former_stat["net"] == -50000
    print("✅ آزمون‌های ریاضیات تسویه، دنگ‌های اعشاری، بدهی دورانی و اعضای سابق ۱۰۰٪ پاس شدند.")

    # -------------------------------------------------------------
    # سناریو ۵: تست دیتابیس، چند کارتی، ارتقای خودکار و حذف
    # -------------------------------------------------------------
    print("\n--- [بخش ۵] آزمون یکپارچگی دیتابیس، مدیریت کارت‌ها و ارتقای پیش‌فرض ---")
    import cloud_db_sync
    # غیرفعال‌سازی موقت ارتباط اینترنتی برای تست داخلی
    async def mock_coro(*args, **kwargs): return True
    cloud_db_sync.backup_to_cloud = mock_coro
    cloud_db_sync.restore_from_cloud = mock_coro

    test_db_file = "test_exhaustive.db"
    if os.path.exists(test_db_file):
        os.remove(test_db_file)
    db.DB_PATH = test_db_file
    
    await db.init_db()

    # ۱. ثبت کاربر
    user_id = 777001
    await db.upsert_user(user_id, "puriya_test", "پوریا ایزی", "پوریا")
    calling = await db.get_user_calling_name(user_id)
    assert calling == "پوریا"

    # ۲. ثبت کارت اول (باید به طور خودکار پیش‌فرض شود)
    c1_id, is_new1 = await db.add_user_card(user_id, "6037997511112222", "بانک ملی")
    assert is_new1 is True
    card_info1 = await db.get_user_card(user_id)
    assert card_info1["card_number"] == "6037997511112222"
    assert card_info1["bank_name"] == "بانک ملی"

    # ۳. ثبت کارت دوم (نباید پیش‌فرض شود)
    c2_id, is_new2 = await db.add_user_card(user_id, "6219861233334444", "بانک سامان")
    assert is_new2 is True
    cards_list = await db.get_user_cards(user_id)
    assert len(cards_list) == 2
    assert cards_list[0]["id"] == c1_id  # کارت اول پیش‌فرض در صدر لیست
    assert cards_list[0]["is_default"] == 1
    assert cards_list[1]["is_default"] == 0

    # ۴. تلاش برای ثبت مجدد همان کارت اول (باید جلوگیری کند و False بدهد)
    c1_dup_id, is_new_dup = await db.add_user_card(user_id, "6037997511112222", "بانک ملی")
    assert is_new_dup is False
    assert c1_dup_id == c1_id
    assert len(await db.get_user_cards(user_id)) == 2

    # ۵. تغییر کارت پیش‌فرض به کارت دوم
    set_def_res = await db.set_default_card(user_id, c2_id)
    assert set_def_res is True
    cards_after_def = await db.get_user_cards(user_id)
    assert cards_after_def[0]["id"] == c2_id
    assert cards_after_def[0]["is_default"] == 1

    # ۶. حذف کارت پیش‌فرض (کارت دوم) -> کارت اول باید خودکار ارتقا یافته و پیش‌فرض شود
    del_res = await db.delete_user_card(user_id, c2_id)
    assert del_res is True
    cards_after_del = await db.get_user_cards(user_id)
    assert len(cards_after_del) == 1
    assert cards_after_del[0]["id"] == c1_id
    assert cards_after_del[0]["is_default"] == 1
    cur_card = await db.get_user_card(user_id)
    assert cur_card["card_number"] == "6037997511112222"

    # ۷. حذف آخرین کارت باقی‌مانده
    del_last = await db.delete_user_card(user_id, c1_id)
    assert del_last is True
    assert len(await db.get_user_cards(user_id)) == 0
    empty_card = await db.get_user_card(user_id)
    assert empty_card["card_number"] is None
    print("✅ تست چرخه حیات چند کارتی و ارتقای خودکار کارت پیش‌فرض پاس شد.")

    # -------------------------------------------------------------
    # سناریو ۶: تست فرآیند گروه، لینک دعوت، و صفر کردن حساب
    # -------------------------------------------------------------
    print("\n--- [بخش ۶] آزمون چرخه حیات گروه، عضویت و تسویه کامل ---")
    creator_id = 1000
    member_b_id = 2000
    member_c_id = 3000
    await db.upsert_user(creator_id, "creator", "مدیر گروه", "مدیر")
    await db.upsert_user(member_b_id, "b_user", "رضا رضایی", "رضا")
    await db.upsert_user(member_c_id, "c_user", "سارا کریمی", "سارا")

    grp_id, inv_code = await db.create_group("دورهمی تعطیلات 🏕️", creator_id)
    assert grp_id > 0
    assert len(inv_code) == 8

    # عضویت اعضا
    is_new_b, nick_b = await db.add_group_member(grp_id, member_b_id)
    assert is_new_b is True
    # تلاش برای عضویت مجدد کاربر B (نباید تکراری شود)
    is_new_b_dup, _ = await db.add_group_member(grp_id, member_b_id)
    assert is_new_b_dup is False
    assert len(await db.get_group_members(grp_id)) == 2

    # افزودن کاربر C
    await db.add_group_member(grp_id, member_c_id)
    assert len(await db.get_group_members(grp_id)) == 3

    # ثبت هزینه اول: مدیر ۳۰۰ هزار برای هر ۳ نفر پرداخت می‌کند
    e1 = await db.add_expense(grp_id, creator_id, "ویلا", 300000, {
        creator_id: 100000,
        member_b_id: 100000,
        member_c_id: 100000
    })
    assert e1 > 0

    # بررسی فعال بودن هزینه
    active_before = await db.get_active_expenses(grp_id)
    assert len(active_before) == 1

    # تست ویرایش مبلغ هزینه فعال (افزایش از ۳۰۰ هزار به ۴۵۰ هزار)
    e1_data = await db.get_expense_by_id(e1, grp_id)
    assert e1_data is not None and e1_data["amount"] == 300000
    upd_res, _ = await db.update_expense_amount(e1, grp_id, 450000)
    assert upd_res is True
    e1_updated = await db.get_expense_by_id(e1, grp_id)
    assert e1_updated["amount"] == 450000
    assert all(s["share_amount"] == 150000 for s in e1_updated["shares"])

    # صفر کردن حساب‌های گروه
    settled_cnt = await db.settle_group(grp_id)
    assert settled_cnt == 1

    # تست جلوگیری از ویرایش هزینه بعد از تسویه کامل حساب
    upd_after_settle, settle_err = await db.update_expense_amount(e1, grp_id, 600000)
    assert upd_after_settle is False
    assert "تسویه شده" in settle_err

    # بررسی خالی شدن هزینه‌های فعال
    active_after = await db.get_active_expenses(grp_id)
    assert len(active_after) == 0

    # بررسی موجود بودن در تاریخچه
    history = await db.get_group_history(grp_id)
    assert len(history) == 1
    assert history[0]["settled"] == 1

    # حذف گروه توسط کاربر غیرسازنده (باید ریجکت شود)
    del_unauth = await db.delete_group(grp_id, member_b_id)
    assert del_unauth is False

    # حذف گروه توسط سازنده (باید با موفقیت تمام رکوردها را پاک کند)
    del_auth = await db.delete_group(grp_id, creator_id)
    assert del_auth is True
    assert (await db.get_group_by_id(grp_id)) is None
    print("✅ آزمون چرخه گروه، تسویه حساب‌ها و مجوزهای امنیتی سرگروه پاس شد.")

    # -------------------------------------------------------------
    # سناریو ۷: ممیزی دقیق طول تمام دکمه‌های اینلاین تلگرام (سقف ۶۴ بایت)
    # -------------------------------------------------------------
    print("\n--- [بخش ۷] ممیزی محدودیت ۶۴ بایتی تمام کلیدهای اینلاین تلگرام ---")
    # شبیه‌سازی بزرگترین شناسه‌های تلگرام و دیتابیس (بدترین حالت ممکن)
    BIG_GRP = 999999
    BIG_USER = 9999999999
    BIG_EXP = 999999
    BIG_AMT = 999999999
    BIG_CARD = 999999

    keyboards_to_test = [
        kb.main_menu_keyboard(),
        kb.groups_list_keyboard([{"id": BIG_GRP, "title": "تست", "member_count": 5}]),
        kb.group_dashboard_keyboard(BIG_GRP, is_creator=True),
        kb.group_dashboard_keyboard(BIG_GRP, is_creator=False),
        kb.group_delete_confirm_keyboard(BIG_GRP),
        kb.members_kick_keyboard(BIG_GRP, [{"id": BIG_USER, "full_name": "تست"}], creator_id=1),
        kb.kick_confirm_keyboard(BIG_GRP, BIG_USER),
        kb.tone_selection_keyboard(BIG_GRP, "friendly"),
        kb.cards_list_keyboard([{"id": BIG_CARD, "card_number": "6037991122334455", "bank_name": "ملی", "is_default": 1}]),
        kb.card_detail_keyboard(BIG_CARD, is_default=False),
        kb.card_delete_confirm_keyboard(BIG_CARD),
        kb.group_naming_choice_keyboard(),
        kb.group_naming_confirm_keyboard(),
        kb.payer_select_keyboard(BIG_GRP, [{"id": BIG_USER, "full_name": "تست"}], BIG_USER),
        kb.shares_select_keyboard(BIG_GRP, [{"id": BIG_USER, "full_name": "تست"}], {BIG_USER}),
        kb.zero_confirm_keyboard(BIG_GRP),
        kb.expense_history_keyboard([{"id": BIG_EXP, "title": "خرید", "amount": BIG_AMT, "settled": 0}], BIG_GRP),
        kb.single_expense_keyboard(BIG_EXP, BIG_GRP, can_edit=False),
        kb.single_expense_keyboard(BIG_EXP, BIG_GRP, can_edit=True),
        kb.cancel_keyboard(BIG_GRP),
        kb.food_picker_keyboard(BIG_GRP, 3),
        kb.food_result_keyboard(BIG_GRP)
    ]

    # همچنین کلیدهای داینامیک درون reports.py و motivational.py
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from motivational import quote_dismiss_keyboard
    reports_dynamic_kb = [
        InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="تست اعلام", callback_data=f"pay:notify:{BIG_GRP}:{BIG_USER}:{BIG_USER}:{BIG_AMT}"),
            InlineKeyboardButton(text="تست یادآوری", callback_data=f"pay:remind:{BIG_GRP}:{BIG_USER}:{BIG_USER}:{BIG_AMT}")
        ]]),
        InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="تایید", callback_data=f"grp:zero_appr:{BIG_GRP}:{BIG_USER}"),
            InlineKeyboardButton(text="رد", callback_data=f"grp:zero_rej:{BIG_GRP}:{BIG_USER}")
        ]]),
        InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="تایید واریز", callback_data=f"pay:ack:{BIG_USER}:{BIG_USER}:{BIG_AMT}"),
            InlineKeyboardButton(text="عدم واریز", callback_data=f"pay:nack:{BIG_USER}:{BIG_USER}")
        ]]),
        quote_dismiss_keyboard()
    ]
    keyboards_to_test.extend(reports_dynamic_kb)

    # تست سیستم ثبت و پاکسازی پیام‌های قبلی چت
    test_uid = 888111
    await db.record_chat_message(test_uid, 101)
    await db.record_chat_message(test_uid, 102)
    await db.record_chat_message(test_uid, 103)
    cleared_ids = await db.get_and_clear_chat_messages(test_uid)
    assert cleared_ids == [101, 102, 103], f"Expected [101, 102, 103], got {cleared_ids}"
    assert len(await db.get_and_clear_chat_messages(test_uid)) == 0

    total_buttons_tested = 0
    for kb_obj in keyboards_to_test:
        for row in kb_obj.inline_keyboard:
            for btn in row:
                if btn.callback_data:
                    total_buttons_tested += 1
                    data_bytes = btn.callback_data.encode("utf-8")
                    byte_len = len(data_bytes)
                    assert byte_len <= 64, f"❌ خطای تلگرام! طول callback_data بیشتر از ۶۴ بایت است: '{btn.callback_data}' ({byte_len} بایت)"

    print(f"✅ تمام {total_buttons_tested} دکمه اینلاین تست شدند و همگی کمتر از ۶۴ بایت بودند.")

    # پاکسازی فایل موقت تست
    if os.path.exists(test_db_file):
        os.remove(test_db_file)

    print("\n" + "=" * 60)
    print("🎉 تمامی تست‌های جامع در تمام سناریوهای مرزی با موفقیت ۱۰۰٪ پاس شدند!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_all_scenarios())
