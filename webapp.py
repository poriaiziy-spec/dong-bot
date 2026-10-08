import json
import logging
from aiohttp import web
import aiosqlite

import database as db
from config import DB_PATH, WEB_APP_URL
from calculator import calculate_group_balances
from motivational import CAFE_MOTIVATIONAL_QUOTES
from bank_utils import format_card_number, detect_bank_name, clean_card_input
from helpers import format_amount

logger = logging.getLogger(__name__)

# قالب کامل و مدرن مینی‌اپ تلگرام (Single Page Application)
MINI_APP_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>کافه دنگ ☕ | مینی‌اپ</title>
    <!-- تلگرام وب‌اپ SDK رسمی -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-color: #0f172a;
            --surface-color: #1e293b;
            --surface-light: #283548;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-amber: #f59e0b;
            --accent-amber-glow: rgba(245, 158, 11, 0.2);
            --accent-emerald: #10b981;
            --accent-emerald-glow: rgba(16, 185, 129, 0.2);
            --accent-rose: #f43f5e;
            --accent-rose-glow: rgba(244, 63, 94, 0.2);
            --accent-sky: #38bdf8;
            --border-color: #334155;
            --radius-sm: 8px;
            --radius-md: 14px;
            --radius-lg: 20px;
            --radius-full: 9999px;
            --font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --bottom-nav-height: 68px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: var(--font-family);
            background-color: var(--bg-color);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            padding-bottom: calc(var(--bottom-nav-height) + 24px);
            overflow-x: hidden;
            user-select: none;
        }

        /* هدر اپلیکیشن */
        .app-header {
            position: sticky;
            top: 0;
            z-index: 50;
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .brand-box {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .brand-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
            box-shadow: 0 4px 12px var(--accent-amber-glow);
        }

        .brand-title {
            font-size: 1.05rem;
            font-weight: 800;
            color: var(--text-primary);
        }

        .brand-subtitle {
            font-size: 0.72rem;
            color: var(--accent-amber);
            font-weight: 500;
        }

        .user-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            padding: 6px 12px;
            border-radius: var(--radius-full);
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }

        .user-pill:active {
            transform: scale(0.96);
            background: var(--surface-light);
        }

        .avatar-dot {
            width: 10px;
            height: 10px;
            background: var(--accent-emerald);
            border-radius: 50%;
            box-shadow: 0 0 8px var(--accent-emerald);
        }

        /* کانتینر اصلی */
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 16px;
        }

        /* کارت‌ها و المان‌های مشترک */
        .card {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-lg);
            padding: 18px;
            margin-bottom: 16px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 14px;
        }

        .card-title {
            font-size: 1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* خلاصه مالی و ترازها */
        .balance-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 14px;
        }

        .balance-item {
            background: var(--bg-color);
            border-radius: var(--radius-md);
            padding: 14px 12px;
            text-align: center;
            border: 1px solid var(--border-color);
        }

        .balance-item.credit {
            border-color: rgba(16, 185, 129, 0.4);
            background: linear-gradient(180deg, rgba(16, 185, 129, 0.05) 0%, rgba(15, 23, 42, 0.6) 100%);
        }

        .balance-item.debt {
            border-color: rgba(244, 63, 94, 0.4);
            background: linear-gradient(180deg, rgba(244, 63, 94, 0.05) 0%, rgba(15, 23, 42, 0.6) 100%);
        }

        .balance-label {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }

        .balance-value {
            font-size: 1.15rem;
            font-weight: 800;
        }

        .balance-value.green { color: var(--accent-emerald); }
        .balance-value.red { color: var(--accent-rose); }
        .balance-value.gold { color: var(--accent-amber); }

        .overall-banner {
            background: linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(30, 41, 59, 0.7));
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: var(--radius-md);
            padding: 12px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.88rem;
        }

        /* اسلایدر/چیپ‌های گروه‌ها */
        .groups-scroll {
            display: flex;
            gap: 10px;
            overflow-x: auto;
            padding-bottom: 8px;
            margin-bottom: 16px;
            scrollbar-width: none;
        }
        .groups-scroll::-webkit-scrollbar { display: none; }

        .group-chip {
            flex: 0 0 auto;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-full);
            padding: 8px 16px;
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .group-chip.active {
            background: var(--accent-amber);
            color: #0f172a;
            border-color: var(--accent-amber);
            box-shadow: 0 4px 14px var(--accent-amber-glow);
        }

        /* کارت بانکی شکیل */
        .bank-card {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid #475569;
            border-radius: var(--radius-md);
            padding: 16px;
            margin-bottom: 10px;
            position: relative;
            overflow: hidden;
        }

        .bank-card::after {
            content: "💳";
            position: absolute;
            left: -10px;
            bottom: -15px;
            font-size: 4.5rem;
            opacity: 0.07;
            pointer-events: none;
        }

        .bank-name {
            font-size: 0.85rem;
            color: var(--accent-amber);
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .card-number-box {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 10px;
            font-family: monospace, var(--font-family);
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: 2px;
            direction: ltr;
        }

        .copy-btn {
            background: rgba(245, 158, 11, 0.15);
            color: var(--accent-amber);
            border: 1px solid var(--accent-amber);
            padding: 4px 10px;
            border-radius: var(--radius-sm);
            font-size: 0.75rem;
            cursor: pointer;
            font-family: var(--font-family);
            font-weight: 600;
            transition: all 0.2s;
        }

        .copy-btn:active {
            transform: scale(0.92);
            background: var(--accent-amber);
            color: #0f172a;
        }

        /* کارت جمله روز کافه‌ای */
        .quote-card {
            background: linear-gradient(135deg, #1e293b, #2a1f1d);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: var(--radius-lg);
            padding: 18px;
            margin-bottom: 16px;
            position: relative;
        }

        .quote-text {
            font-size: 0.95rem;
            font-weight: 500;
            color: #fef08a;
            line-height: 1.8;
            text-align: center;
        }

        /* فرم‌ها و اینپوت‌ها */
        .form-group {
            margin-bottom: 16px;
        }

        .form-label {
            display: block;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 6px;
            color: var(--text-secondary);
        }

        .form-control {
            width: 100%;
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 12px 14px;
            font-family: var(--font-family);
            font-size: 0.95rem;
            color: var(--text-primary);
            transition: border-color 0.2s;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--accent-amber);
            box-shadow: 0 0 0 2px var(--accent-amber-glow);
        }

        .segmented-control {
            display: flex;
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 4px;
            margin-bottom: 16px;
        }

        .segment-btn {
            flex: 1;
            padding: 8px 12px;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            font-family: var(--font-family);
            font-size: 0.85rem;
            font-weight: 600;
            border-radius: var(--radius-sm);
            cursor: pointer;
            transition: all 0.2s;
        }

        .segment-btn.active {
            background: var(--surface-color);
            color: var(--text-primary);
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            font-weight: 700;
        }

        .btn-primary {
            width: 100%;
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: #0f172a;
            border: none;
            border-radius: var(--radius-md);
            padding: 14px;
            font-family: var(--font-family);
            font-size: 1rem;
            font-weight: 800;
            cursor: pointer;
            box-shadow: 0 4px 16px var(--accent-amber-glow);
            transition: transform 0.15s, opacity 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .btn-primary:active {
            transform: scale(0.98);
            opacity: 0.9;
        }

        /* لیست اقلام خرید و هزینه‌ها */
        .item-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 14px;
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            margin-bottom: 8px;
        }

        .item-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .item-title {
            font-size: 0.92rem;
            font-weight: 700;
        }

        .item-sub {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .item-price {
            font-size: 0.95rem;
            font-weight: 800;
            color: var(--accent-amber);
            text-align: left;
        }

        .del-btn {
            background: rgba(244, 63, 94, 0.15);
            color: var(--accent-rose);
            border: 1px solid var(--accent-rose);
            border-radius: var(--radius-sm);
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 0.85rem;
            margin-right: 8px;
        }

        /* چک‌باکس‌های اعضا در فرم ثبت هزینه */
        .members-checklist {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 8px;
        }

        .member-checkbox-label {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            padding: 8px 12px;
            border-radius: var(--radius-sm);
            font-size: 0.85rem;
            cursor: pointer;
        }

        .member-checkbox-label input {
            accent-color: var(--accent-amber);
        }

        /* گردونه غذا */
        .wheel-container {
            text-align: center;
            padding: 24px 0;
        }

        .food-slot-box {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 2px dashed var(--accent-amber);
            border-radius: var(--radius-lg);
            padding: 30px 20px;
            margin-bottom: 20px;
            min-height: 140px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 24px var(--accent-amber-glow);
        }

        .food-emoji {
            font-size: 3rem;
            margin-bottom: 8px;
            animation: bounce 1s infinite alternate;
        }

        @keyframes bounce {
            from { transform: translateY(0); }
            to { transform: translateY(-8px); }
        }

        .food-name {
            font-size: 1.4rem;
            font-weight: 800;
            color: #fef08a;
        }

        .food-category-pill {
            font-size: 0.8rem;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* نوار ناوبری پایین صفحه (Bottom Dock) */
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            height: var(--bottom-nav-height);
            background: rgba(15, 23, 42, 0.94);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-top: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-around;
            z-index: 100;
            max-width: 600px;
            margin: 0 auto;
        }

        .nav-btn {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-family: var(--font-family);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 4px;
            font-size: 0.72rem;
            font-weight: 600;
            cursor: pointer;
            flex: 1;
            height: 100%;
            transition: all 0.2s;
        }

        .nav-btn .icon {
            font-size: 1.3rem;
            transition: transform 0.2s;
        }

        .nav-btn.active {
            color: var(--accent-amber);
            font-weight: 800;
        }

        .nav-btn.active .icon {
            transform: translateY(-2px) scale(1.15);
        }

        /* نوتیفیکیشن / Toast */
        .toast {
            position: fixed;
            top: 70px;
            left: 50%;
            transform: translateX(-50%) translateY(-20px);
            background: #1e293b;
            color: #f8fafc;
            border: 1px solid var(--accent-amber);
            padding: 10px 20px;
            border-radius: var(--radius-full);
            font-size: 0.88rem;
            font-weight: 600;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            z-index: 200;
            opacity: 0;
            pointer-events: none;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .toast.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }

        /* لودر و محتوای خالی */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-secondary);
        }

        .empty-icon {
            font-size: 2.5rem;
            margin-bottom: 12px;
            opacity: 0.7;
        }

        .loading-spinner {
            display: inline-block;
            width: 32px;
            height: 32px;
            border: 3px solid rgba(245, 158, 11, 0.2);
            border-radius: 50%;
            border-top-color: var(--accent-amber);
            animation: spin 0.8s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .tab-content { display: none; }
        .tab-content.active { display: block; }
    </style>
</head>
<body>

    <!-- هدر بالای صفحه -->
    <header class="app-header">
        <div class="brand-box">
            <div class="brand-icon">☕</div>
            <div>
                <div class="brand-title">کافه دنگ</div>
                <div class="brand-subtitle">پارتنر حساب و کتاب دورهمی</div>
            </div>
        </div>
        <div class="user-pill" id="userPill" onclick="promptSwitchUser()">
            <span class="avatar-dot"></span>
            <span id="userNameHeader">در حال اتصال...</span>
        </div>
    </header>

    <!-- کانتینر اصلی محتوا -->
    <main class="container">

        <!-- تب ۱: داشبورد من -->
        <section id="tab-dashboard" class="tab-content active">
            <!-- کارت خوش‌آمدگویی و تراز کل -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">📊 وضعیت مالی حساب من</div>
                    <span id="refreshBtn" style="cursor:pointer; font-size:1.1rem;" onclick="loadData()">🔄</span>
                </div>
                <div class="balance-grid">
                    <div class="balance-item credit">
                        <div class="balance-label">طلبکاری‌های من 💚</div>
                        <div class="balance-value green" id="statCreditor">۰ تومان</div>
                    </div>
                    <div class="balance-item debt">
                        <div class="balance-label">بدهکاری‌های من 🔴</div>
                        <div class="balance-value red" id="statDebtor">۰ تومان</div>
                    </div>
                </div>
                <div class="overall-banner" id="statOverallBanner">
                    <span>تراز کلی شما:</span>
                    <strong id="statNetTotal" class="green">۰ تومان</strong>
                </div>
            </div>

            <!-- کارت جمله انگیزشی روز -->
            <div class="quote-card">
                <div style="font-size:0.75rem; color:#fde68a; margin-bottom:6px; text-align:center;">☕ جرعه‌ای حس خوب کافه‌ای:</div>
                <div class="quote-text" id="dailyQuoteText">قهوه‌ت رو بنوش، نفس عمیق بکش؛ قشنگ‌ترین اتفاق‌ها همیشه بی‌خبر میان ✨</div>
            </div>

            <!-- کارت‌های بانکی من -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">💳 شماره کارت‌های من</div>
                    <button class="copy-btn" onclick="openAddCardModal()">➕ افزودن کارت</button>
                </div>
                <div id="cardsListContainer">
                    <div class="empty-state">
                        <div class="loading-spinner"></div>
                        <p style="margin-top:10px;">در حال بارگذاری اطلاعات...</p>
                    </div>
                </div>
            </div>

            <!-- میانبرهای سریع -->
            <div class="card">
                <div class="card-title" style="margin-bottom:12px;">⚡ دسترسی‌های سریع</div>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;">
                    <button class="copy-btn" style="padding:12px 6px; font-size:0.8rem;" onclick="switchTab('add-expense')">➕ ثبت هزینه</button>
                    <button class="copy-btn" style="padding:12px 6px; font-size:0.8rem;" onclick="switchTab('shopping')">🛒 لیست خرید</button>
                    <button class="copy-btn" style="padding:12px 6px; font-size:0.8rem;" onclick="switchTab('food')">🍕 گردونه غذا</button>
                </div>
            </div>
        </section>

        <!-- تب ۲: گروه‌ها و دنگ‌ها -->
        <section id="tab-groups" class="tab-content">
            <!-- چیپ‌های انتخاب گروه -->
            <div class="groups-scroll" id="groupsChipsContainer">
                <!-- دکمه‌های گروه‌ها از طریق جاوااسکریپت پر می‌شوند -->
            </div>

            <div id="activeGroupDetailCard">
                <!-- اطلاعات تفصیلی گروه انتخاب شده -->
            </div>
        </section>

        <!-- تب ۳: ثبت هزینه سریع -->
        <section id="tab-add-expense" class="tab-content">
            <div class="card">
                <div class="card-title" style="margin-bottom:14px;">💸 ثبت سریع هزینه جدید</div>
                
                <div class="form-group">
                    <label class="form-label">گروه مورد نظر:</label>
                    <select id="expenseGroupSelect" class="form-control" onchange="onExpenseGroupChange()">
                        <!-- گزینه‌های گروه‌ها -->
                    </select>
                </div>

                <div class="form-group">
                    <label class="form-label">عنوان هزینه (برای چی خرج کردی؟):</label>
                    <input type="text" id="expenseTitleInput" class="form-control" placeholder="مثلاً: پیتزا و نوشابه، بنزین، سوپرمارکت...">
                </div>

                <label class="form-label">روش محاسبه مبلغ:</label>
                <div class="segmented-control">
                    <button class="segment-btn active" id="segSimple" onclick="setExpenseMode('simple')">مبلغ کل</button>
                    <button class="segment-btn" id="segQty" onclick="setExpenseMode('qty')">قیمت واحد × تعداد 🔢</button>
                </div>

                <!-- حالت ۱: مبلغ ساده -->
                <div id="simpleAmountBox" class="form-group">
                    <label class="form-label">مبلغ کل (تومان):</label>
                    <input type="number" id="expenseAmountInput" class="form-control" placeholder="مثلاً: 140000" oninput="updateSharePreview()">
                </div>

                <!-- حالت ۲: قیمت واحد × تعداد -->
                <div id="qtyAmountBox" style="display:none;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px;">
                        <div>
                            <label class="form-label">قیمت هر واحد (تومان):</label>
                            <input type="number" id="expenseUnitPriceInput" class="form-control" placeholder="35000" oninput="calcQtyTotal()">
                        </div>
                        <div>
                            <label class="form-label">تعداد یا مقدار:</label>
                            <input type="number" id="expenseQuantityInput" class="form-control" placeholder="4" step="0.5" oninput="calcQtyTotal()">
                        </div>
                    </div>
                    <div class="overall-banner" style="margin-bottom:14px;">
                        <span>مبلغ کل محاسبه‌شده:</span>
                        <strong id="qtyCalculatedTotal" class="green">۰ تومان</strong>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">پرداخت‌کننده (کی حساب کرده؟):</label>
                    <select id="expensePayerSelect" class="form-control">
                        <!-- اعضای گروه -->
                    </select>
                </div>

                <div class="form-group">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
                        <label class="form-label" style="margin:0;">کسانی که در دنگ سهیم هستند:</label>
                        <span style="font-size:0.75rem; color:var(--accent-amber); cursor:pointer;" onclick="toggleAllExpenseMembers()">انتخاب / لغو همه</span>
                    </div>
                    <div class="members-checklist" id="expenseMembersChecklist">
                        <!-- چک‌باکس اعضا -->
                    </div>
                </div>

                <div class="overall-banner" style="margin-bottom:16px;">
                    <span>سهم هر نفر:</span>
                    <strong id="previewPerShare" class="green">۰ تومان</strong>
                </div>

                <button class="btn-primary" onclick="submitNewExpense()">
                    <span>✅ ثبت نهایی هزینه</span>
                </button>
            </div>
        </section>

        <!-- تب ۴: فاکتور و لیست خرید -->
        <section id="tab-shopping" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div class="card-title">🛒 فاکتور و لیست خرید گروه</div>
                    <select id="shoppingGroupSelect" class="form-control" style="width:auto; padding:6px 12px; font-size:0.85rem;" onchange="renderShoppingList()">
                    </select>
                </div>

                <!-- فرم افزودن سریع قلم -->
                <div style="background:var(--bg-color); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px; margin-bottom:16px;">
                    <div style="font-size:0.88rem; font-weight:700; margin-bottom:10px; color:var(--accent-amber);">➕ افزودن قلم جدید به فاکتور:</div>
                    <div class="form-group" style="margin-bottom:8px;">
                        <input type="text" id="shopItemName" class="form-control" placeholder="نام قلم (مثلاً: گوشت چرخ‌کرده، نان، نوشابه)">
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-bottom:10px;">
                        <input type="number" id="shopItemUnitPrice" class="form-control" placeholder="قیمت واحد (تومان)" oninput="calcShopPreview()">
                        <input type="number" id="shopItemQuantity" class="form-control" placeholder="تعداد یا کیلو (پیش‌فرض: ۱)" step="0.5" oninput="calcShopPreview()">
                    </div>
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:10px; font-size:0.85rem;">
                        <span style="color:var(--text-secondary);">قیمت کل قلم:</span>
                        <strong id="shopItemTotalPreview" style="color:var(--accent-amber);">۰ تومان</strong>
                    </div>
                    <button class="btn-primary" style="padding:10px;" onclick="submitNewShoppingItem()">
                        <span>افزودن به لیست خرید</span>
                    </button>
                </div>

                <!-- لیست اقلام فاکتور -->
                <div id="shoppingItemsContainer">
                    <!-- اقلام با جاوااسکریپت پر می‌شوند -->
                </div>

                <!-- جمع کل فاکتور -->
                <div class="overall-banner" style="margin-top:14px;">
                    <span>جمع کل فاکتور خرید:</span>
                    <strong id="shoppingGrandTotal" class="green">۰ تومان</strong>
                </div>
            </div>
        </section>

        <!-- تب ۵: گردونه غذا -->
        <section id="tab-food" class="tab-content">
            <div class="card wheel-container">
                <div class="card-title" style="justify-content:center; margin-bottom:8px;">🍕 چی بخوریم؟ (گردونه شانس دورهمی)</div>
                <p style="font-size:0.82rem; color:var(--text-secondary); margin-bottom:16px;">
                    نمی‌دونید برای دورهمی چی سفارش بدید؟ بذارید کافه دنگ رندوم براتون انتخاب کنه! 😋
                </p>

                <div class="segmented-control" style="margin-bottom:16px;">
                    <button class="segment-btn active" onclick="setFoodCategory('all', this)">همه 🎲</button>
                    <button class="segment-btn" onclick="setFoodCategory('fastfood', this)">فست‌فود 🍔</button>
                    <button class="segment-btn" onclick="setFoodCategory('traditional', this)">سنتی 🍢</button>
                    <button class="segment-btn" onclick="setFoodCategory('cafe', this)">کافه ☕</button>
                    <button class="segment-btn" onclick="setFoodCategory('custom', this)">پیشنهادی ✨</button>
                </div>

                <div class="food-slot-box" id="foodSlotBox">
                    <div class="food-emoji" id="foodEmoji">🍕</div>
                    <div class="food-name" id="foodName">روی دکمه بچرخون بزنید!</div>
                    <div class="food-category-pill" id="foodDesc">پیشنهاد خوشمزه برای دورهمی شما</div>
                </div>

                <button class="btn-primary" id="spinFoodBtn" onclick="spinFoodWheel()" style="margin-bottom:14px;">
                    <span>🎲 بچرخون و انتخاب کن!</span>
                </button>

                <!-- بخش افزودن غذای دلخواه جدید به گردونه -->
                <div style="background:var(--bg-color); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px; margin-top:16px; text-align:right;">
                    <div style="font-size:0.92rem; font-weight:700; margin-bottom:10px; color:var(--accent-amber); display:flex; align-items:center; gap:6px;">
                        <span>➕ افزودن غذای دلخواه به گزینه‌ها:</span>
                    </div>
                    <div class="form-group" style="margin-bottom:10px;">
                        <input type="text" id="customFoodInput" class="form-control" placeholder="نام غذا (مثلاً: پاستا آلفردو، ساندویچ بندری، دیزی...)">
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px;">
                        <div>
                            <label class="form-label" style="font-size:0.75rem;">دسته‌بندی:</label>
                            <select id="customFoodCatSelect" class="form-control" style="padding:8px 10px; font-size:0.85rem;">
                                <option value="fastfood">فست‌فود 🍔</option>
                                <option value="traditional">سنتی و خوراک 🍢</option>
                                <option value="cafe">کافه و دسر ☕</option>
                                <option value="custom">دست‌ساز و خودمونی 🍳</option>
                            </select>
                        </div>
                        <div>
                            <label class="form-label" style="font-size:0.75rem;">ایموجی یا آیکون:</label>
                            <select id="customFoodEmojiSelect" class="form-control" style="padding:8px 10px; font-size:0.85rem;">
                                <option value="🍕">🍕 پیتزا</option>
                                <option value="🍔">🍔 برگر</option>
                                <option value="🍢">🍢 کباب</option>
                                <option value="🍲">🍲 خورشت / پلو</option>
                                <option value="🥪">🥪 ساندویچ</option>
                                <option value="🍝">🍝 پاستا</option>
                                <option value="🍗">🍗 سوخاری</option>
                                <option value="☕">☕ کافه / دسر</option>
                                <option value="🍳">🍳 خودمونی</option>
                                <option value="🍽️">🍽️ خوراک</option>
                            </select>
                        </div>
                    </div>
                    <button class="btn-primary" style="padding:10px; font-size:0.9rem;" onclick="submitNewCustomFood()">
                        <span>➕ ثبت و اضافه به گردونه</span>
                    </button>

                    <!-- لیست غذاهای اضافه شده -->
                    <div style="margin-top:16px;">
                        <div style="font-size:0.82rem; font-weight:700; color:var(--text-secondary); margin-bottom:8px;">
                            📋 غذاهای اضافه شده توسط شما و گروه:
                        </div>
                        <div id="customFoodsListContainer">
                            <!-- به صورت پویا پر می‌شود -->
                        </div>
                    </div>
                </div>
            </div>
        </section>

    </main>

    <!-- نوار ناوبری پایین صفحه (Dock) -->
    <nav class="bottom-nav">
        <button class="nav-btn active" id="btn-dashboard" onclick="switchTab('dashboard')">
            <span class="icon">🏠</span>
            <span>داشبورد</span>
        </button>
        <button class="nav-btn" id="btn-groups" onclick="switchTab('groups')">
            <span class="icon">👥</span>
            <span>گروه‌ها</span>
        </button>
        <button class="nav-btn" id="btn-add-expense" onclick="switchTab('add-expense')">
            <span class="icon">➕</span>
            <span>ثبت هزینه</span>
        </button>
        <button class="nav-btn" id="btn-shopping" onclick="switchTab('shopping')">
            <span class="icon">🛒</span>
            <span>خرید</span>
        </button>
        <button class="nav-btn" id="btn-food" onclick="switchTab('food')">
            <span class="icon">🍕</span>
            <span>چی بخوریم</span>
        </button>
    </nav>

    <!-- توست پیام موقت -->
    <div class="toast" id="toastMessage">
        <span>✨</span>
        <span id="toastText">عملیات با موفقیت انجام شد</span>
    </div>

    <script>
        // اتصال به تلگرام وب‌اپ
        const tg = window.Telegram?.WebApp;
        if (tg) {
            try {
                tg.ready();
                tg.expand();
                if (tg.setHeaderColor) tg.setHeaderColor('#0f172a');
                if (tg.setBackgroundColor) tg.setBackgroundColor('#0f172a');
            } catch(e) {
                console.log('TG Init note:', e);
            }
        }

        // متغیرهای وضعیت کلاینت
        let appState = {
            userId: null,
            userData: null,
            currentGroupId: null,
            expenseMode: 'simple',
            selectedFoodCategory: 'all'
        };

        // فهرست غذاهای کافه دنگ
        const FOOD_DATABASE = [
            { name: "پیتزا پپرونی تند و کش‌دار", emoji: "🍕", cat: "fastfood", desc: "همیشه اولین گزینه دورهمی‌های پایه‌ست!" },
            { name: "چیزبرگر دوبل با سیب‌زمینی سرخ‌کرده", emoji: "🍔", cat: "fastfood", desc: "آبدار و مشتی، هیچکی دست رد به سینه‌ش نمی‌زنه!" },
            { name: "مرغ سوخاری اسپایسی (استریپس)", emoji: "🍗", cat: "fastfood", desc: "ترد، داغ و سیرکننده برای یه جمع چند نفره." },
            { name: "ساندویچ هات‌داگ پنیری تنوری", emoji: "🌭", cat: "fastfood", desc: "سریع، نوستالژیک و پرملات!" },
            { name: "کباب کوبیده نگین‌دار با نان سنگک و ریحان", emoji: "🍢", cat: "traditional", desc: "اصیل‌ترین مزه ایرانی؛ بوی کباب دیوونه می‌کنه!" },
            { name: "جوجه کباب زعفرانی با برنج کته کره", emoji: "🍗", cat: "traditional", desc: "غذای مطمئن و خوش‌طعم که همه عاشقشن." },
            { name: "قورمه‌سبزی جاافتاده با ته‌دیگ زعفرانی", emoji: "🍲", cat: "traditional", desc: "عطر شنبلیله و لیمو عمانی، نجات‌بخش تمام دورهمی‌ها!" },
            { name: "دیزی سنگی مشتی با ترشی و دوغ محلی", emoji: "🥘", cat: "traditional", desc: "کوبیدنش با بچه‌ها خودش یه تفریح جداگانه‌ست!" },
            { name: "وافل نوتلا و موز با توت‌فرنگی تازه", emoji: "🧇", cat: "cafe", desc: "شیرین، انرژی‌بخش و عالی کنار یک فنجون لاته." },
            { name: "کیک شکلاتی خیس با بستنی وانیلی", emoji: "🍰", cat: "cafe", desc: "بمب شکلات برای بالا بردن دوپامین جمع!" },
            { name: "آیس‌کارامل ماکیاتو خنک", emoji: "☕", cat: "cafe", desc: "قهوه خنک با عطر شیرین کارامل، رفع‌کننده هر خستگی." },
            { name: "املت گوجه‌فرنگی قهوه‌خانه‌ای پرپیاز", emoji: "🍳", cat: "traditional", desc: "ساده، اقتصادی، رفاقتی و از همه‌چی خوشمزه‌تر!" }
        ];

        // عدد فرمت شده به ریال/تومان
        function formatToman(num) {
            if (num === null || num === undefined) return "۰";
            return Number(num).toLocaleString('fa-IR') + " تومان";
        }

        // نمایش Toast
        function showToast(text) {
            const toast = document.getElementById('toastMessage');
            document.getElementById('toastText').innerText = text;
            toast.classList.add('show');
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2500);
        }

        // کپی شماره کارت
        function copyText(text, label) {
            navigator.clipboard.writeText(text).then(() => {
                showToast((label || 'متن') + ' کپی شد ✨');
            }).catch(() => {
                const input = document.createElement('input');
                input.value = text;
                document.body.appendChild(input);
                input.select();
                document.execCommand('copy');
                document.body.removeChild(input);
                showToast((label || 'متن') + ' کپی شد ✨');
            });
        }

        // تعویض تب‌ها
        function switchTab(tabId) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
            
            const targetTab = document.getElementById('tab-' + tabId);
            const targetBtn = document.getElementById('btn-' + tabId);
            if (targetTab) targetTab.classList.add('active');
            if (targetBtn) targetBtn.classList.add('active');

            if (tg?.HapticFeedback) {
                tg.HapticFeedback.selectionChanged();
            }

            if (tabId === 'groups') renderGroupsTab();
            if (tabId === 'shopping') renderShoppingList();
            if (tabId === 'add-expense') prepareExpenseForm();
            if (tabId === 'food') renderCustomFoodsList();
        }

        // بارگذاری داده‌ها از بک‌اند
        async function loadData() {
            try {
                let url = '/api/app/user_data';
                // بررسی کاربر تلگرام
                if (tg?.initDataUnsafe?.user?.id) {
                    appState.userId = tg.initDataUnsafe.user.id;
                    url += '?user_id=' + appState.userId;
                } else if (appState.userId) {
                    url += '?user_id=' + appState.userId;
                }

                // بررسی پارامتر query string مثلا ?group_id=...
                const urlParams = new URLSearchParams(window.location.search);
                const qGroupId = urlParams.get('group_id');
                if (qGroupId) appState.currentGroupId = parseInt(qGroupId);

                const res = await fetch(url);
                if (!res.ok) throw new Error('خطا در دریافت اطلاعات');
                const data = await res.json();
                appState.userData = data;
                appState.customFoods = data.custom_foods || [];

                if (data.user) {
                    appState.userId = data.user.id;
                    document.getElementById('userNameHeader').innerText = data.user.calling_name || data.user.full_name || 'کاربر گرامی';
                }

                // بروزرسانی داشبورد
                renderDashboard(data);
                renderCustomFoodsList();

                // مقداردهی اولیه گروه
                if (data.groups && data.groups.length > 0) {
                    if (!appState.currentGroupId || !data.groups.some(g => g.id === appState.currentGroupId)) {
                        appState.currentGroupId = data.groups[0].id;
                    }
                }

                showToast('اطلاعات به‌روز شد ☕');
            } catch (err) {
                console.error(err);
                document.getElementById('userNameHeader').innerText = 'خطا در ارتباط';
            }
        }

        // رندر صفحه داشبورد
        function renderDashboard(data) {
            const stats = data.overall_stats || { total_creditor: 0, total_debtor: 0, net_total: 0 };
            document.getElementById('statCreditor').innerText = formatToman(stats.total_creditor);
            document.getElementById('statDebtor').innerText = formatToman(stats.total_debtor);
            
            const netEl = document.getElementById('statNetTotal');
            if (stats.net_total > 0) {
                netEl.innerText = '+' + formatToman(stats.net_total) + ' (طلبکار)';
                netEl.className = 'balance-value green';
            } else if (stats.net_total < 0) {
                netEl.innerText = formatToman(stats.net_total) + ' (بدهکار)';
                netEl.className = 'balance-value red';
            } else {
                netEl.innerText = 'بی‌حساب و صاف ✨';
                netEl.className = 'balance-value gold';
            }

            if (data.daily_quote) {
                document.getElementById('dailyQuoteText').innerText = data.daily_quote;
            }

            // رندر کارت‌های بانکی
            const cardsContainer = document.getElementById('cardsListContainer');
            if (data.cards && data.cards.length > 0) {
                let html = '';
                data.cards.forEach(c => {
                    const cleanNum = c.card_number.replace(/\D/g, '');
                    const formatted = cleanNum.replace(/(\d{4})/g, '$1 ').trim();
                    html += `
                        <div class="bank-card">
                            <div class="bank-name">
                                <span>${c.bank_name || 'بانک'}</span>
                                ${c.is_default ? '<span style="font-size:0.75rem; color:#fef08a;">★ کارت اصلی</span>' : ''}
                            </div>
                            <div class="card-number-box">
                                <span>${formatted}</span>
                                <button class="copy-btn" onclick="copyText('${cleanNum}', 'شماره کارت')">کپی</button>
                            </div>
                        </div>
                    `;
                });
                cardsContainer.innerHTML = html;
            } else {
                cardsContainer.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">💳</div>
                        <p>هنوز شماره کارتی ثبت نکردی جان دلم!</p>
                        <button class="copy-btn" style="margin-top:8px;" onclick="openAddCardModal()">➕ ثبت اولین کارت</button>
                    </div>
                `;
            }
        }

        // رندر تب گروه‌ها
        function renderGroupsTab() {
            const data = appState.userData;
            if (!data || !data.groups || data.groups.length === 0) {
                document.getElementById('groupsChipsContainer').innerHTML = '';
                document.getElementById('activeGroupDetailCard').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">👥</div>
                        <p>شما هنوز عضو گروهی نیستید قشنگم!</p>
                    </div>
                `;
                return;
            }

            // چیپ‌های گروه‌ها
            let chipsHtml = '';
            data.groups.forEach(g => {
                const activeCls = g.id === appState.currentGroupId ? 'active' : '';
                chipsHtml += `
                    <div class="group-chip ${activeCls}" onclick="selectGroup(${g.id})">
                        <span>📁</span>
                        <span>${g.title}</span>
                    </div>
                `;
            });
            document.getElementById('groupsChipsContainer').innerHTML = chipsHtml;

            // جزئیات گروه فعال
            const currentGroup = data.groups.find(g => g.id === appState.currentGroupId) || data.groups[0];
            if (!currentGroup) return;

            let groupHtml = `
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">🏕️ ${currentGroup.title}</div>
                            <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:2px;">
                                ${currentGroup.members.length} عضو • کد دعوت: <code>${currentGroup.invite_code}</code>
                            </div>
                        </div>
                        <button class="copy-btn" onclick="copyInviteLink('${currentGroup.invite_code}')">💌 لینک دعوت</button>
                    </div>

                    <!-- بخش تسویه حساب بدهی‌ها -->
                    <div style="margin-top:16px;">
                        <div style="font-size:0.9rem; font-weight:700; margin-bottom:8px; color:var(--accent-amber);">
                            ⚖️ فرمول تسویه حساب بدهی‌ها:
                        </div>
            `;

            const settlements = currentGroup.balances?.settlements || [];
            if (settlements.length > 0) {
                settlements.forEach(s => {
                    const fromUser = s.from_user || {};
                    const toUser = s.to_user || {};
                    const fromName = s.from_name || fromUser.display_name || fromUser.nickname || fromUser.calling_name || fromUser.full_name || 'عضو';
                    const toName = s.to_name || toUser.display_name || toUser.nickname || toUser.calling_name || toUser.full_name || 'عضو';
                    const toUserCard = s.to_card;
                    const toUserCardFormatted = s.to_card_formatted || (toUserCard ? toUserCard.replace(/(\d{4})/g, '$1 ').trim() : '');
                    
                    groupHtml += `
                        <div class="item-row" style="flex-direction:column; align-items:stretch; gap:10px; padding:14px; margin-bottom:10px;">
                            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                                <div style="font-size:0.95rem; font-weight:700;">
                                    <span style="color:var(--accent-rose);">${fromName}</span>
                                    <span style="color:var(--text-secondary); font-size:0.82rem; margin:0 6px;">بدهد به ➔</span>
                                    <span style="color:var(--accent-emerald);">${toName}</span>
                                </div>
                                <div class="item-price" style="font-size:1.05rem;">${formatToman(s.amount)}</div>
                            </div>
                            ${toUserCard ? `
                                <div style="display:flex; align-items:center; justify-content:space-between; background:rgba(15,23,42,0.6); padding:8px 12px; border-radius:var(--radius-sm); border:1px solid var(--border-color);">
                                    <div style="font-size:0.78rem; color:var(--text-secondary); display:flex; align-items:center; gap:6px;">
                                        <span>💳 شماره کارت:</span>
                                        <span style="font-family:monospace; direction:ltr; unicode-bidi:embed; font-size:0.92rem; color:var(--text-primary); font-weight:700; letter-spacing:1px;">${toUserCardFormatted}</span>
                                    </div>
                                    <button class="copy-btn" onclick="copyText('${toUserCard}', 'شماره کارت')">کپی کارت</button>
                                </div>
                            ` : `
                                <div style="font-size:0.75rem; color:var(--text-muted);">
                                    (شماره کارت طلبکار هنوز ثبت نشده است)
                                </div>
                            `}
                        </div>
                    `;
                });
            } else {
                groupHtml += `
                    <div style="background:var(--bg-color); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px; text-align:center; color:var(--accent-emerald); font-size:0.88rem;">
                        ✨ تمام حساب‌ها در این گروه صاف و تسویه است!
                    </div>
                `;
            }

            // لیست آخرین هزینه‌ها
            groupHtml += `
                    <div style="margin-top:20px;">
                        <div style="font-size:0.9rem; font-weight:700; margin-bottom:8px; color:var(--accent-amber);">
                            💸 هزینه‌های اخیر گروه:
                        </div>
            `;

            const expenses = currentGroup.expenses || [];
            if (expenses.length > 0) {
                expenses.forEach(e => {
                    groupHtml += `
                        <div class="item-row">
                            <div class="item-info">
                                <div class="item-title">${e.title}</div>
                                <div class="item-sub">پرداخت‌کننده: <strong>${e.payer_name}</strong></div>
                            </div>
                            <div class="item-price">${formatToman(e.amount)}</div>
                        </div>
                    `;
                });
            } else {
                groupHtml += `
                    <div style="background:var(--bg-color); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px; text-align:center; color:var(--text-secondary); font-size:0.85rem;">
                        هنوز هزینه‌ای در این دوره ثبت نشده است.
                    </div>
                `;
            }

            // لیست اعضا و تراز فردی
            groupHtml += `
                    <div style="margin-top:20px;">
                        <div style="font-size:0.9rem; font-weight:700; margin-bottom:8px; color:var(--accent-amber);">
                            👥 وضعیت اعضا و دنگ‌ها:
                        </div>
            `;

            const memberStats = currentGroup.balances?.member_stats || [];
            memberStats.forEach(m => {
                const net = m.net || 0;
                let netText = '۰';
                let netCls = 'gold';
                if (net > 0) {
                    netText = '+' + formatToman(net);
                    netCls = 'green';
                } else if (net < 0) {
                    netText = formatToman(net);
                    netCls = 'red';
                }

                groupHtml += `
                    <div class="item-row">
                        <div class="item-info">
                            <div class="item-title">${m.user?.display_name || m.user?.full_name || 'عضو'}</div>
                            <div class="item-sub">پرداختی: ${formatToman(m.paid)} | سهم: ${formatToman(m.owed)}</div>
                        </div>
                        <div class="balance-value ${netCls}" style="font-size:0.95rem;">${netText}</div>
                    </div>
                `;
            });

            groupHtml += `
                    </div>
                </div>
            `;

            document.getElementById('activeGroupDetailCard').innerHTML = groupHtml;
        }

        // انتخاب گروه
        function selectGroup(groupId) {
            appState.currentGroupId = groupId;
            renderGroupsTab();
        }

        // کپی لینک دعوت
        function copyInviteLink(code) {
            const botUsername = 'dong_yar_bot'; // نام کاربری پیش‌فرض یا فعلی
            const link = 'https://t.me/' + botUsername + '?start=join_' + code;
            copyText(link, 'لینک دعوت به گروه');
        }

        // آماده‌سازی فرم ثبت هزینه
        function prepareExpenseForm() {
            const data = appState.userData;
            if (!data || !data.groups || data.groups.length === 0) return;

            const grpSelect = document.getElementById('expenseGroupSelect');
            grpSelect.innerHTML = data.groups.map(g => `<option value="${g.id}" ${g.id === appState.currentGroupId ? 'selected' : ''}>${g.title}</option>`).join('');
            
            onExpenseGroupChange();
        }

        // تغییر گروه در فرم ثبت هزینه
        function onExpenseGroupChange() {
            const groupId = parseInt(document.getElementById('expenseGroupSelect').value);
            const group = appState.userData.groups.find(g => g.id === groupId);
            if (!group) return;

            // لیست پرداخت‌کننده‌ها
            const payerSelect = document.getElementById('expensePayerSelect');
            payerSelect.innerHTML = group.members.map(m => `
                <option value="${m.id}" ${m.id === appState.userId ? 'selected' : ''}>
                    ${m.display_name || m.full_name}
                </option>
            `).join('');

            // لیست اعضای سهیم
            const checklist = document.getElementById('expenseMembersChecklist');
            checklist.innerHTML = group.members.map(m => `
                <label class="member-checkbox-label">
                    <input type="checkbox" class="exp-member-cb" value="${m.id}" checked onchange="updateSharePreview()">
                    <span>${m.display_name || m.full_name}</span>
                </label>
            `).join('');

            updateSharePreview();
        }

        // تغییر حالت ورود مبلغ
        function setExpenseMode(mode) {
            appState.expenseMode = mode;
            if (mode === 'simple') {
                document.getElementById('segSimple').classList.add('active');
                document.getElementById('segQty').classList.remove('active');
                document.getElementById('simpleAmountBox').style.display = 'block';
                document.getElementById('qtyAmountBox').style.display = 'none';
            } else {
                document.getElementById('segSimple').classList.remove('active');
                document.getElementById('segQty').classList.add('active');
                document.getElementById('simpleAmountBox').style.display = 'none';
                document.getElementById('qtyAmountBox').style.display = 'block';
            }
            updateSharePreview();
        }

        // محاسبه ضرب فی × تعداد
        function calcQtyTotal() {
            const unit = parseFloat(document.getElementById('expenseUnitPriceInput').value) || 0;
            const qty = parseFloat(document.getElementById('expenseQuantityInput').value) || 0;
            const total = Math.round(unit * qty);
            document.getElementById('qtyCalculatedTotal').innerText = formatToman(total);
            updateSharePreview();
        }

        // پیش‌نمایش سهم هر فرد
        function updateSharePreview() {
            let total = 0;
            if (appState.expenseMode === 'simple') {
                total = parseInt(document.getElementById('expenseAmountInput').value) || 0;
            } else {
                const unit = parseFloat(document.getElementById('expenseUnitPriceInput').value) || 0;
                const qty = parseFloat(document.getElementById('expenseQuantityInput').value) || 0;
                total = Math.round(unit * qty);
            }

            const cbs = document.querySelectorAll('.exp-member-cb:checked');
            const count = cbs.length;
            if (count > 0 && total > 0) {
                const perShare = Math.round(total / count);
                document.getElementById('previewPerShare').innerText = formatToman(perShare);
            } else {
                document.getElementById('previewPerShare').innerText = '۰ تومان';
            }
        }

        function toggleAllExpenseMembers() {
            const cbs = document.querySelectorAll('.exp-member-cb');
            const allChecked = Array.from(cbs).every(cb => cb.checked);
            cbs.forEach(cb => cb.checked = !allChecked);
            updateSharePreview();
        }

        // ثبت هزینه جدید در سرور
        async function submitNewExpense() {
            const groupId = parseInt(document.getElementById('expenseGroupSelect').value);
            const payerId = parseInt(document.getElementById('expensePayerSelect').value);
            const title = document.getElementById('expenseTitleInput').value.trim();

            let amount = 0;
            if (appState.expenseMode === 'simple') {
                amount = parseInt(document.getElementById('expenseAmountInput').value) || 0;
            } else {
                const unit = parseFloat(document.getElementById('expenseUnitPriceInput').value) || 0;
                const qty = parseFloat(document.getElementById('expenseQuantityInput').value) || 0;
                amount = Math.round(unit * qty);
            }

            if (!title) {
                showToast('⚠️ لطفاً عنوان هزینه را بنویسید');
                return;
            }
            if (amount <= 0) {
                showToast('⚠️ مبلغ هزینه باید بیشتر از صفر باشد');
                return;
            }

            const selectedMemberIds = Array.from(document.querySelectorAll('.exp-member-cb:checked')).map(cb => parseInt(cb.value));
            if (selectedMemberIds.length === 0) {
                showToast('⚠️ حداقل یک نفر باید در دنگ سهیم باشد');
                return;
            }

            // محاسبه سهم مساوی
            const baseShare = Math.floor(amount / selectedMemberIds.length);
            let rem = amount - (baseShare * selectedMemberIds.length);
            const shares = {};
            selectedMemberIds.forEach(uid => {
                shares[uid] = baseShare + (rem > 0 ? 1 : 0);
                if (rem > 0) rem--;
            });

            try {
                const payload = {
                    group_id: groupId,
                    payer_id: payerId,
                    title: title,
                    amount: amount,
                    shares: shares
                };

                const res = await fetch('/api/app/add_expense', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const resData = await res.json();
                if (resData.success) {
                    showToast('🎉 هزینه با موفقیت ثبت شد!');
                    document.getElementById('expenseTitleInput').value = '';
                    document.getElementById('expenseAmountInput').value = '';
                    document.getElementById('expenseUnitPriceInput').value = '';
                    document.getElementById('expenseQuantityInput').value = '';
                    await loadData();
                    switchTab('groups');
                } else {
                    showToast('خطا: ' + (resData.error || 'ثبت نشد'));
                }
            } catch (err) {
                showToast('خطای شبکه در ثبت هزینه');
            }
        }

        // رندر لیست خرید
        function renderShoppingList() {
            const data = appState.userData;
            if (!data || !data.groups || data.groups.length === 0) return;

            const select = document.getElementById('shoppingGroupSelect');
            select.innerHTML = data.groups.map(g => `<option value="${g.id}" ${g.id === appState.currentGroupId ? 'selected' : ''}>${g.title}</option>`).join('');

            const currentGroupId = parseInt(select.value) || appState.currentGroupId;
            const group = data.groups.find(g => g.id === currentGroupId);
            const container = document.getElementById('shoppingItemsContainer');

            if (!group || !group.shopping_items || group.shopping_items.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">🛒</div>
                        <p>لیست خرید این گروه فعلاً خالی است.</p>
                    </div>
                `;
                document.getElementById('shoppingGrandTotal').innerText = '۰ تومان';
                return;
            }

            let html = '';
            let total = 0;
            group.shopping_items.forEach(item => {
                total += item.total_price;
                html += `
                    <div class="item-row">
                        <div class="item-info">
                            <div class="item-title">${item.item_name}</div>
                            <div class="item-sub">
                                فی: ${formatToman(item.unit_price)} × ${item.quantity} عدد
                            </div>
                        </div>
                        <div style="display:flex; align-items:center;">
                            <div class="item-price">${formatToman(item.total_price)}</div>
                            <button class="del-btn" onclick="deleteShoppingItem(${item.id}, ${currentGroupId})">✕</button>
                        </div>
                    </div>
                `;
            });

            container.innerHTML = html;
            document.getElementById('shoppingGrandTotal').innerText = formatToman(total);
        }

        function calcShopPreview() {
            const p = parseFloat(document.getElementById('shopItemUnitPrice').value) || 0;
            const q = parseFloat(document.getElementById('shopItemQuantity').value) || 1;
            document.getElementById('shopItemTotalPreview').innerText = formatToman(Math.round(p * q));
        }

        async function submitNewShoppingItem() {
            const groupId = parseInt(document.getElementById('shoppingGroupSelect').value);
            const name = document.getElementById('shopItemName').value.trim();
            const unitPrice = parseInt(document.getElementById('shopItemUnitPrice').value) || 0;
            const quantity = parseFloat(document.getElementById('shopItemQuantity').value) || 1;

            if (!name) {
                showToast('لطفاً نام قلم را بنویسید');
                return;
            }
            if (unitPrice <= 0) {
                showToast('قیمت واحد باید بیشتر از صفر باشد');
                return;
            }

            try {
                const res = await fetch('/api/app/add_shopping_item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        group_id: groupId,
                        user_id: appState.userId || 1,
                        item_name: name,
                        unit_price: unitPrice,
                        quantity: quantity
                    })
                });
                const resData = await res.json();
                if (resData.success) {
                    showToast('قلم به فاکتور اضافه شد 🛒');
                    document.getElementById('shopItemName').value = '';
                    document.getElementById('shopItemUnitPrice').value = '';
                    document.getElementById('shopItemQuantity').value = '';
                    calcShopPreview();
                    await loadData();
                    renderShoppingList();
                }
            } catch (e) {
                showToast('خطا در ثبت قلم خرید');
            }
        }

        async function deleteShoppingItem(itemId, groupId) {
            try {
                const res = await fetch('/api/app/delete_shopping_item', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ item_id: itemId, group_id: groupId })
                });
                const resData = await res.json();
                if (resData.success) {
                    showToast('قلم از فاکتور حذف شد');
                    await loadData();
                    renderShoppingList();
                }
            } catch (e) {
                showToast('خطا در حذف قلم');
            }
        }

        // گردونه غذا
        function setFoodCategory(cat, btn) {
            appState.selectedFoodCategory = cat;
            document.querySelectorAll('#tab-food .segment-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
        }

        function renderCustomFoodsList() {
            const container = document.getElementById('customFoodsListContainer');
            if (!container) return;
            const list = appState.customFoods || [];
            if (list.length === 0) {
                container.innerHTML = '<div style="font-size:0.75rem; color:var(--text-muted); text-align:center; padding:8px;">هنوز غذای دلخواهی اضافه نشده است.</div>';
                return;
            }
            let html = '<div style="display:flex; flex-direction:column; gap:6px;">';
            list.forEach(f => {
                html += `
                    <div class="item-row" style="padding:8px 12px; margin-bottom:0; justify-content:space-between;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="font-size:1.25rem;">${f.emoji || '🍽️'}</span>
                            <div style="text-align:right;">
                                <div style="font-size:0.88rem; font-weight:700;">${f.name}</div>
                                <div style="font-size:0.72rem; color:var(--text-secondary);">${f.description || 'پیشنهاد اختصاصی شما ✨'}</div>
                            </div>
                        </div>
                        <button class="del-btn" style="width:26px; height:26px; font-size:0.75rem;" onclick="deleteCustomFood(${f.id})">✕</button>
                    </div>
                `;
            });
            html += '</div>';
            container.innerHTML = html;
        }

        async function submitNewCustomFood() {
            const name = document.getElementById('customFoodInput').value.trim();
            const cat = document.getElementById('customFoodCatSelect').value;
            const emoji = document.getElementById('customFoodEmojiSelect').value;

            if (!name) {
                showToast('لطفاً نام غذا را بنویسید');
                return;
            }

            try {
                const res = await fetch('/api/app/add_food', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        group_id: appState.currentGroupId,
                        user_id: appState.userId,
                        name: name,
                        category: cat,
                        emoji: emoji,
                        description: 'پیشنهاد دلخواه دورهمی شما ✨'
                    })
                });
                const resData = await res.json();
                if (resData.success) {
                    showToast('غذای جدید به گردونه اضافه شد 😋✨');
                    document.getElementById('customFoodInput').value = '';
                    await loadData();
                    renderCustomFoodsList();
                } else {
                    showToast('خطا در ثبت غذا');
                }
            } catch(e) {
                showToast('خطا در ارتباط با سرور');
            }
        }

        async function deleteCustomFood(id) {
            try {
                const res = await fetch('/api/app/delete_food', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ food_id: id })
                });
                const resData = await res.json();
                if (resData.success) {
                    showToast('غذا از گردونه حذف شد');
                    await loadData();
                    renderCustomFoodsList();
                }
            } catch (e) {
                showToast('خطا در حذف غذا');
            }
        }

        function spinFoodWheel() {
            let customPool = (appState.customFoods || []).map(f => ({
                name: f.name,
                emoji: f.emoji || '🍽️',
                cat: f.category || 'all',
                desc: f.description || 'پیشنهاد اختصاصی شما ✨'
            }));

            let pool = [...FOOD_DATABASE, ...customPool];
            if (appState.selectedFoodCategory !== 'all') {
                if (appState.selectedFoodCategory === 'custom') {
                    pool = customPool.length > 0 ? customPool : pool;
                } else {
                    pool = pool.filter(f => f.cat === appState.selectedFoodCategory || (f.cat === 'custom' && appState.selectedFoodCategory === 'custom'));
                }
            }
            if (pool.length === 0) pool = [...FOOD_DATABASE, ...customPool];
            if (pool.length === 0) pool = FOOD_DATABASE;

            const btn = document.getElementById('spinFoodBtn');
            btn.disabled = true;
            let counter = 0;
            const interval = setInterval(() => {
                const rand = pool[Math.floor(Math.random() * pool.length)];
                document.getElementById('foodEmoji').innerText = rand.emoji;
                document.getElementById('foodName').innerText = rand.name;
                document.getElementById('foodDesc').innerText = rand.desc;
                counter++;
                if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();

                if (counter > 15) {
                    clearInterval(interval);
                    btn.disabled = false;
                    const finalChoice = pool[Math.floor(Math.random() * pool.length)];
                    document.getElementById('foodEmoji').innerText = finalChoice.emoji;
                    document.getElementById('foodName').innerText = finalChoice.name;
                    document.getElementById('foodDesc').innerText = '🎉 برنده انتخاب شد: ' + finalChoice.desc;
                    if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
                }
            }, 80);
        }

        // افزودن کارت بانکی
        async function openAddCardModal() {
            const cardNum = prompt('شماره کارت ۱۶ رقمی خود را وارد کنید:');
            if (!cardNum) return;
            const bankName = prompt('نام بانک (اختیاری):') || 'بانک';
            try {
                const res = await fetch('/api/app/add_card', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: appState.userId || 1,
                        card_number: cardNum,
                        bank_name: bankName
                    })
                });
                const resData = await res.json();
                if (resData.success) {
                    showToast('کارت بانکی اضافه شد 💳');
                    await loadData();
                } else {
                    showToast('خطا: شماره کارت نامعتبر است');
                }
            } catch (e) {
                showToast('خطا در ثبت کارت');
            }
        }

        // تعویض حساب کاربری در حالت مرورگر
        async function promptSwitchUser() {
            try {
                const res = await fetch('/api/app/users');
                const users = await res.json();
                if (!users || users.length === 0) return;
                let msg = 'شناسه کاربر خود را انتخاب کنید:\\n';
                users.forEach(u => {
                    msg += u.id + ': ' + (u.calling_name || u.full_name) + '\\n';
                });
                const chosen = prompt(msg, appState.userId || users[0].id);
                if (chosen) {
                    appState.userId = parseInt(chosen);
                    await loadData();
                }
            } catch (e) {}
        }

        // شروع برنامه
        window.addEventListener('DOMContentLoaded', () => {
            loadData();
        });
    </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# روت‌ها و API های وب‌سرور برای مینی‌اپ تلگرام
# ---------------------------------------------------------------------------

async def miniapp_page_handler(request: web.Request) -> web.Response:
    """صفحه اختصاصی مینی‌اپ تلگرام"""
    return web.Response(text=MINI_APP_HTML, content_type="text/html", charset="utf-8")


async def api_users_handler(request: web.Request) -> web.Response:
    """دریافت لیست کاربران فعال جهت سوئیچ پروفایل یا تست"""
    try:
        async with aiosqlite.connect(DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT id, full_name, calling_name, username FROM users WHERE is_active = 1 LIMIT 50") as cur:
                rows = [dict(r) for r in await cur.fetchall()]
        return web.json_response(rows, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def api_user_data_handler(request: web.Request) -> web.Response:
    """دریافت بسته کامل اطلاعات کاربر برای مینی‌اپ (پروفایل، گروه‌ها، ترازها، کارت‌ها)"""
    try:
        user_id_param = request.query.get("user_id")
        user_id = int(user_id_param) if user_id_param and user_id_param.isdigit() else None

        async with aiosqlite.connect(DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row
            # اگر کاربری داده نشده بود، اولین کاربر موجود را پیدا کن
            if not user_id:
                async with conn.execute("SELECT id FROM users ORDER BY id ASC LIMIT 1") as cur:
                    row = await cur.fetchone()
                    if row:
                        user_id = row[0]
                    else:
                        user_id = 1

            # اطلاعات پروفایل کاربر
            async with conn.execute("SELECT id, full_name, calling_name, username, card_number, bank_name FROM users WHERE id = ?", (user_id,)) as cur:
                user_row = await cur.fetchone()
                user = dict(user_row) if user_row else {"id": user_id, "full_name": "کاربر مهمان", "calling_name": "کاربر گرامی"}

        # کارت‌های بانکی کاربر
        cards = await db.get_user_cards(user_id)

        # گروه‌های کاربر
        groups = await db.get_user_groups(user_id)
        
        total_creditor = 0
        total_debtor = 0
        groups_payload = []

        for g in groups:
            gid = g["id"]
            members = await db.get_group_members(gid)
            active_expenses = await db.get_active_expenses(gid)
            balances = calculate_group_balances(members, active_expenses)
            shopping_items = await db.get_group_shopping_items(gid)

            # افزودن کارت طلبکار به فرمول تسویه و تضمین نام‌های خوانا
            for s in balances.get("settlements", []):
                from_u = s.get("from_user") or {}
                to_u = s.get("to_user") or {}
                if not s.get("from_name"):
                    s["from_name"] = from_u.get("display_name") or from_u.get("nickname") or from_u.get("calling_name") or from_u.get("full_name") or "عضو"
                if not s.get("to_name"):
                    s["to_name"] = to_u.get("display_name") or to_u.get("nickname") or to_u.get("calling_name") or to_u.get("full_name") or "عضو"

                to_uid = to_u.get("id") or s.get("to_id")
                if to_uid:
                    s_card = await db.get_user_card(to_uid)
                    raw_card = s_card.get("card_number") if s_card else None
                    s["to_card"] = raw_card
                    if raw_card:
                        digits = "".join(filter(str.isdigit, str(raw_card)))
                        if len(digits) == 16:
                            s["to_card_formatted"] = f"{digits[:4]} {digits[4:8]} {digits[8:12]} {digits[12:]}"
                        else:
                            s["to_card_formatted"] = raw_card
                    else:
                        s["to_card_formatted"] = None

            # استخراج تراز این کاربر در گروه
            user_stat = next((m for m in balances.get("member_stats", []) if m["user"]["id"] == user_id), None)
            user_net = user_stat["net"] if user_stat else 0
            if user_net > 0:
                total_creditor += user_net
            elif user_net < 0:
                total_debtor += abs(user_net)

            groups_payload.append({
                "id": gid,
                "title": g["title"],
                "invite_code": g["invite_code"],
                "tone": g.get("tone", "friendly"),
                "members": members,
                "expenses": active_expenses,
                "balances": balances,
                "shopping_items": shopping_items
            })

        import random
        daily_quote = random.choice(CAFE_MOTIVATIONAL_QUOTES)
        custom_foods = await db.get_custom_foods()

        data = {
            "user": user,
            "cards": cards,
            "groups": groups_payload,
            "custom_foods": custom_foods,
            "overall_stats": {
                "total_creditor": total_creditor,
                "total_debtor": total_debtor,
                "net_total": total_creditor - total_debtor
            },
            "daily_quote": daily_quote
        }
        return web.json_response(data, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logger.error(f"api_user_data_handler error: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def api_add_expense_handler(request: web.Request) -> web.Response:
    """ثبت مستقیم هزینه از طریق مینی‌اپ"""
    try:
        body = await request.json()
        group_id = int(body["group_id"])
        payer_id = int(body["payer_id"])
        title = str(body["title"]).strip()
        amount = int(body["amount"])
        raw_shares = body["shares"]
        shares = {int(k): int(v) for k, v in raw_shares.items()}

        if amount <= 0 or not title or not shares:
            return web.json_response({"success": False, "error": "ورودی نامعتبر"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        exp_id = await db.add_expense(group_id, payer_id, title, amount, shares)
        return web.json_response({"success": True, "expense_id": exp_id}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logger.error(f"api_add_expense_handler error: {e}", exc_info=True)
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def api_add_shopping_item_handler(request: web.Request) -> web.Response:
    """ثبت قلم جدید در فاکتور خرید از طریق مینی‌اپ"""
    try:
        body = await request.json()
        group_id = int(body["group_id"])
        user_id = int(body["user_id"])
        item_name = str(body["item_name"]).strip()
        unit_price = int(body["unit_price"])
        quantity = float(body.get("quantity", 1))

        if not item_name or unit_price <= 0:
            return web.json_response({"success": False, "error": "ورودی نامعتبر"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        it_id = await db.add_shopping_item(group_id, user_id, item_name, unit_price, quantity)
        return web.json_response({"success": True, "item_id": it_id}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logger.error(f"api_add_shopping_item_handler error: {e}", exc_info=True)
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def api_delete_shopping_item_handler(request: web.Request) -> web.Response:
    """حذف قلم فاکتور از طریق مینی‌اپ"""
    try:
        body = await request.json()
        item_id = int(body["item_id"])
        group_id = int(body["group_id"])
        res = await db.delete_shopping_item(item_id, group_id)
        return web.json_response({"success": bool(res)}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def api_add_card_handler(request: web.Request) -> web.Response:
    """افزودن کارت بانکی از طریق مینی‌اپ"""
    try:
        body = await request.json()
        user_id = int(body["user_id"])
        card_number = str(body["card_number"]).strip()
        bank_name = str(body.get("bank_name") or "").strip()

        clean = clean_card_input(card_number)
        if not clean:
            return web.json_response({"success": False, "error": "شماره کارت ۱۶ رقمی معتبر نیست"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        if not bank_name:
            bank_name = detect_bank_name(clean) or "بانک"

        card_id, _ = await db.add_user_card(user_id, clean, bank_name)
        return web.json_response({"success": True, "card_id": card_id}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def api_add_food_handler(request: web.Request) -> web.Response:
    """افزودن غذای دلخواه جدید به گردونه از طریق مینی‌اپ"""
    try:
        body = await request.json()
        group_id = int(body["group_id"]) if body.get("group_id") else None
        user_id = int(body["user_id"]) if body.get("user_id") else None
        name = str(body["name"]).strip()
        category = str(body.get("category") or "all")
        emoji = str(body.get("emoji") or "🍽️")
        description = str(body.get("description") or "پیشنهاد دلخواه دورهمی شما ✨")

        if not name:
            return web.json_response({"success": False, "error": "نام غذا نمی‌تواند خالی باشد"}, status=400, headers={"Access-Control-Allow-Origin": "*"})

        food_id = await db.add_custom_food(group_id, user_id, name, category, emoji, description)
        return web.json_response({"success": True, "food_id": food_id}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        logger.error(f"api_add_food_handler error: {e}", exc_info=True)
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


async def api_delete_food_handler(request: web.Request) -> web.Response:
    """حذف غذای سفارشی از طریق مینی‌اپ"""
    try:
        body = await request.json()
        food_id = int(body["food_id"])
        res = await db.delete_custom_food(food_id)
        return web.json_response({"success": bool(res)}, headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers={"Access-Control-Allow-Origin": "*"})


def setup_webapp_routes(app: web.Application):
    """ثبت تمام مسیرهای مربوط به مینی‌اپ در اپلیکیشن aiohttp"""
    app.router.add_get("/app", miniapp_page_handler)
    app.router.add_get("/api/app/users", api_users_handler)
    app.router.add_get("/api/app/user_data", api_user_data_handler)
    app.router.add_post("/api/app/add_expense", api_add_expense_handler)
    app.router.add_post("/api/app/add_shopping_item", api_add_shopping_item_handler)
    app.router.add_post("/api/app/delete_shopping_item", api_delete_shopping_item_handler)
    app.router.add_post("/api/app/add_card", api_add_card_handler)
    app.router.add_post("/api/app/add_food", api_add_food_handler)
    app.router.add_post("/api/app/delete_food", api_delete_food_handler)
