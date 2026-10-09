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

# ===========================================================================
# قالب اولترا-مدرن، لوکس و حرفه‌ای مینی‌اپ تلگرام (Single Page Application)
# ===========================================================================
MINI_APP_HTML = r"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>کافه دنگ ☕ | مینی‌اپ اختصاصی</title>
    <!-- تلگرام وب‌اپ SDK رسمی -->
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #080c14;
            --bg-card: rgba(18, 24, 38, 0.78);
            --bg-card-hover: rgba(26, 35, 54, 0.85);
            --bg-inner: rgba(10, 15, 26, 0.7);
            --border-glass: rgba(255, 255, 255, 0.08);
            --border-glass-active: rgba(245, 158, 11, 0.4);
            
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --text-muted: #64748b;
            
            --gold-primary: #f59e0b;
            --gold-secondary: #d97706;
            --gold-glow: rgba(245, 158, 11, 0.28);
            
            --emerald-main: #10b981;
            --emerald-glow: rgba(16, 185, 129, 0.22);
            
            --rose-main: #f43f5e;
            --rose-glow: rgba(244, 63, 94, 0.22);
            
            --sky-main: #38bdf8;
            --radius-sm: 10px;
            --radius-md: 16px;
            --radius-lg: 24px;
            --radius-full: 9999px;
            --font-family: 'Vazirmatn', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --dock-height: 70px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: var(--font-family);
            background-color: var(--bg-base);
            background-image: 
                radial-gradient(circle at 15% 15%, rgba(245, 158, 11, 0.09) 0%, transparent 45%),
                radial-gradient(circle at 85% 65%, rgba(16, 185, 129, 0.07) 0%, transparent 45%),
                radial-gradient(circle at 50% 95%, rgba(56, 189, 248, 0.06) 0%, transparent 40%);
            background-attachment: fixed;
            color: var(--text-main);
            line-height: 1.6;
            min-height: 100vh;
            padding-bottom: calc(var(--dock-height) + 36px);
            overflow-x: hidden;
            user-select: none;
        }

        /* کانواس جشن و افکت‌های تعاملی */
        #confettiCanvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 999;
        }

        /* هدر اپلیکیشن */
        .app-header {
            position: sticky;
            top: 0;
            z-index: 50;
            background: rgba(8, 12, 20, 0.82);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-bottom: 1px solid var(--border-glass);
            padding: 12px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .brand-box {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-icon-box {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #f59e0b 0%, #b45309 100%);
            border-radius: var(--radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            box-shadow: 0 8px 20px var(--gold-glow);
            position: relative;
            overflow: hidden;
        }

        .brand-icon-box::after {
            content: '';
            position: absolute;
            top: 0; left: 0; right: 0; height: 50%;
            background: linear-gradient(180deg, rgba(255,255,255,0.25) 0%, transparent 100%);
        }

        .brand-title {
            font-size: 1.15rem;
            font-weight: 900;
            letter-spacing: -0.5px;
            background: linear-gradient(135deg, #ffffff 0%, #fef08a 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .brand-subtitle {
            font-size: 0.72rem;
            color: var(--gold-primary);
            font-weight: 600;
        }

        .user-pill {
            display: flex;
            align-items: center;
            gap: 9px;
            background: rgba(22, 30, 49, 0.7);
            border: 1px solid var(--border-glass);
            padding: 7px 14px;
            border-radius: var(--radius-full);
            font-size: 0.86rem;
            font-weight: 700;
            cursor: pointer;
            backdrop-filter: blur(12px);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .user-pill:active {
            transform: scale(0.95);
            background: rgba(30, 41, 59, 0.9);
            border-color: var(--gold-primary);
        }

        .avatar-glow-dot {
            width: 9px;
            height: 9px;
            background: var(--emerald-main);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--emerald-main);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1.1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        /* کانتینر اصلی */
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 16px;
        }

        /* کارت‌ها و کانتینرهای شیشه‌ای (Glass Cards) */
        .card {
            background: var(--bg-card);
            backdrop-filter: blur(28px);
            -webkit-backdrop-filter: blur(28px);
            border: 1px solid var(--border-glass);
            border-radius: var(--radius-lg);
            padding: 20px;
            margin-bottom: 18px;
            box-shadow: 0 14px 35px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08);
            position: relative;
            overflow: hidden;
            transition: transform 0.25s, box-shadow 0.25s;
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }

        .card-title {
            font-size: 1.05rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* مسترکارت / کارت اصلی مالی داشبورد */
        .hero-wallet-card {
            background: linear-gradient(135deg, #1e293b 0%, #111827 50%, #090d16 100%);
            border: 1px solid rgba(245, 158, 11, 0.25);
            border-radius: var(--radius-lg);
            padding: 22px;
            margin-bottom: 20px;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5), inset 0 1px 1px rgba(255, 255, 255, 0.15);
            position: relative;
            overflow: hidden;
        }

        .hero-wallet-card::before {
            content: '';
            position: absolute;
            top: -50px;
            left: -50px;
            width: 130px;
            height: 130px;
            background: radial-gradient(circle, var(--gold-glow) 0%, transparent 70%);
            pointer-events: none;
        }

        .wallet-card-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }

        .card-chip {
            width: 38px;
            height: 28px;
            background: linear-gradient(135deg, #d97706, #fbbf24);
            border-radius: 6px;
            position: relative;
            box-shadow: inset 0 1px 2px rgba(255,255,255,0.4);
        }

        .card-chip::after {
            content: '';
            position: absolute;
            top: 50%; left: 0; right: 0; height: 1px;
            background: rgba(0,0,0,0.3);
        }

        .hero-balance-label {
            font-size: 0.8rem;
            color: var(--text-sub);
            margin-bottom: 4px;
        }

        .hero-balance-amount {
            font-size: 1.95rem;
            font-weight: 900;
            letter-spacing: -0.5px;
            margin-bottom: 16px;
        }

        .balance-split-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            background: var(--bg-inner);
            border-radius: var(--radius-md);
            padding: 12px 14px;
            border: 1px solid var(--border-glass);
        }

        .split-item {
            display: flex;
            flex-direction: column;
            gap: 2px;
        }

        .split-label {
            font-size: 0.74rem;
            color: var(--text-sub);
        }

        .split-val {
            font-size: 1rem;
            font-weight: 800;
        }

        .split-val.green { color: var(--emerald-main); }
        .split-val.red { color: var(--rose-main); }

        /* کارت بانکی عابربانک مدرن */
        .bank-card {
            background: linear-gradient(135deg, #162032 0%, #0d131f 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: var(--radius-md);
            padding: 18px;
            margin-bottom: 12px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s;
        }

        .bank-card:active {
            transform: scale(0.99);
        }

        .bank-card-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }

        .bank-name-badge {
            font-size: 0.88rem;
            font-weight: 800;
            color: var(--gold-primary);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .card-number-box {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-top: 10px;
            font-family: monospace, var(--font-family);
            font-size: 1.25rem;
            font-weight: 800;
            letter-spacing: 2.5px;
            direction: ltr;
            color: #ffffff;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }

        .copy-btn {
            background: rgba(245, 158, 11, 0.16);
            color: var(--gold-primary);
            border: 1px solid var(--gold-primary);
            padding: 6px 14px;
            border-radius: var(--radius-sm);
            font-size: 0.8rem;
            cursor: pointer;
            font-family: var(--font-family);
            font-weight: 700;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .copy-btn:active {
            transform: scale(0.92);
            background: var(--gold-primary);
            color: #080c14;
        }

        /* کارت جمله روز کافه‌ای */
        .quote-card {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(42, 31, 29, 0.7) 100%);
            border: 1px solid rgba(245, 158, 11, 0.28);
            border-radius: var(--radius-lg);
            padding: 20px;
            margin-bottom: 18px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.25);
            position: relative;
        }

        .quote-header {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            font-size: 0.78rem;
            color: #fef08a;
            font-weight: 700;
            margin-bottom: 10px;
            letter-spacing: 0.5px;
        }

        .quote-text {
            font-size: 0.98rem;
            font-weight: 600;
            color: #fffbeb;
            line-height: 1.9;
            text-align: center;
        }

        /* اسلایدر/چیپ‌های انتخاب گروه */
        .groups-scroll {
            display: flex;
            gap: 10px;
            overflow-x: auto;
            padding-bottom: 10px;
            margin-bottom: 18px;
            scrollbar-width: none;
        }
        .groups-scroll::-webkit-scrollbar { display: none; }

        .group-chip {
            flex: 0 0 auto;
            background: rgba(22, 30, 49, 0.7);
            border: 1px solid var(--border-glass);
            border-radius: var(--radius-full);
            padding: 9px 18px;
            font-size: 0.88rem;
            font-weight: 700;
            color: var(--text-sub);
            cursor: pointer;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .group-chip.active {
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #080c14;
            border-color: #f59e0b;
            box-shadow: 0 6px 18px var(--gold-glow);
            transform: translateY(-1px);
        }

        /* ردیف‌های تسویه و هزینه‌ها */
        .item-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 16px;
            background: var(--bg-inner);
            border: 1px solid var(--border-glass);
            border-radius: var(--radius-md);
            margin-bottom: 10px;
            transition: border-color 0.2s, background 0.2s;
        }

        .item-row:hover {
            border-color: rgba(255, 255, 255, 0.15);
            background: rgba(14, 21, 35, 0.85);
        }

        .item-price {
            font-size: 1.05rem;
            font-weight: 900;
            color: var(--gold-primary);
            text-align: left;
        }

        /* دکمه‌ها و فرم‌ها */
        .form-group {
            margin-bottom: 18px;
        }

        .form-label {
            display: block;
            font-size: 0.88rem;
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--text-sub);
        }

        .form-control {
            width: 100%;
            background: var(--bg-inner);
            border: 1px solid var(--border-glass);
            border-radius: var(--radius-md);
            padding: 13px 16px;
            font-family: var(--font-family);
            font-size: 0.96rem;
            color: var(--text-main);
            transition: all 0.2s;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--gold-primary);
            box-shadow: 0 0 0 3px var(--gold-glow);
            background: rgba(15, 23, 42, 0.9);
        }

        .segmented-control {
            display: flex;
            background: var(--bg-inner);
            border: 1px solid var(--border-glass);
            border-radius: var(--radius-md);
            padding: 4px;
            margin-bottom: 18px;
        }

        .segment-btn {
            flex: 1;
            padding: 9px 14px;
            border: none;
            background: transparent;
            color: var(--text-sub);
            font-family: var(--font-family);
            font-size: 0.86rem;
            font-weight: 700;
            border-radius: var(--radius-sm);
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .segment-btn.active {
            background: rgba(30, 41, 59, 0.95);
            color: #ffffff;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            font-weight: 800;
        }

        .btn-primary {
            width: 100%;
            background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
            color: #080c14;
            border: none;
            border-radius: var(--radius-md);
            padding: 15px;
            font-family: var(--font-family);
            font-size: 1.02rem;
            font-weight: 900;
            cursor: pointer;
            box-shadow: 0 6px 20px var(--gold-glow);
            transition: transform 0.15s, opacity 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .btn-primary:active {
            transform: scale(0.98);
            opacity: 0.92;
        }

        .del-btn {
            background: rgba(244, 63, 94, 0.15);
            color: var(--rose-main);
            border: 1px solid var(--rose-main);
            border-radius: var(--radius-sm);
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 0.88rem;
            transition: transform 0.2s;
        }

        .del-btn:active {
            transform: scale(0.9);
        }

        /* چک‌باکس اعضا در فرم ثبت هزینه */
        .members-checklist {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 10px;
        }

        .member-checkbox-label {
            display: flex;
            align-items: center;
            gap: 9px;
            background: var(--bg-inner);
            border: 1px solid var(--border-glass);
            padding: 10px 14px;
            border-radius: var(--radius-md);
            font-size: 0.88rem;
            cursor: pointer;
            transition: border-color 0.2s;
        }

        .member-checkbox-label input {
            accent-color: var(--gold-primary);
            width: 16px;
            height: 16px;
        }

        /* گردونه غذا */
        .wheel-container {
            text-align: center;
            padding: 16px 0;
        }

        .food-slot-box {
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.9));
            border: 2px dashed rgba(245, 158, 11, 0.5);
            border-radius: var(--radius-lg);
            padding: 32px 20px;
            margin-bottom: 20px;
            min-height: 155px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            box-shadow: 0 12px 30px var(--gold-glow);
            position: relative;
        }

        .food-emoji {
            font-size: 3.5rem;
            margin-bottom: 10px;
            animation: bounce 1.2s infinite alternate;
        }

        @keyframes bounce {
            from { transform: translateY(0); }
            to { transform: translateY(-10px); }
        }

        .food-name {
            font-size: 1.5rem;
            font-weight: 900;
            color: #fef08a;
            text-shadow: 0 2px 8px rgba(0,0,0,0.5);
        }

        .food-category-pill {
            font-size: 0.82rem;
            color: var(--text-sub);
            margin-top: 6px;
            font-weight: 600;
        }

        /* نوار ناوبری شناور و شیشه‌ای پایین (Floating Glass Dock) */
        .floating-dock-wrapper {
            position: fixed;
            bottom: 14px;
            left: 0;
            right: 0;
            display: flex;
            justify-content: center;
            z-index: 100;
            padding: 0 16px;
            pointer-events: none;
        }

        .bottom-dock {
            pointer-events: auto;
            width: 100%;
            max-width: 520px;
            height: var(--dock-height);
            background: rgba(13, 19, 32, 0.88);
            backdrop-filter: blur(28px);
            -webkit-backdrop-filter: blur(28px);
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: var(--radius-full);
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.15);
            display: flex;
            align-items: center;
            justify-content: space-around;
            padding: 0 8px;
        }

        .nav-dock-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-family: var(--font-family);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 3px;
            font-size: 0.72rem;
            font-weight: 700;
            cursor: pointer;
            flex: 1;
            height: 100%;
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
        }

        .nav-dock-btn .nav-icon {
            font-size: 1.35rem;
            transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .nav-dock-btn.active {
            color: var(--gold-primary);
        }

        .nav-dock-btn.active .nav-icon {
            transform: translateY(-3px) scale(1.18);
        }

        .nav-dock-btn.active::after {
            content: '';
            position: absolute;
            bottom: 6px;
            width: 14px;
            height: 3px;
            background: var(--gold-primary);
            border-radius: var(--radius-full);
            box-shadow: 0 0 8px var(--gold-primary);
        }

        /* نوتیفیکیشن / Toast شناور لوکس */
        .toast {
            position: fixed;
            top: 75px;
            left: 50%;
            transform: translateX(-50%) translateY(-25px);
            background: rgba(18, 24, 38, 0.95);
            color: var(--text-main);
            border: 1px solid var(--gold-primary);
            padding: 11px 24px;
            border-radius: var(--radius-full);
            font-size: 0.9rem;
            font-weight: 700;
            box-shadow: 0 14px 40px rgba(0, 0, 0, 0.5), 0 0 20px var(--gold-glow);
            z-index: 200;
            opacity: 0;
            pointer-events: none;
            backdrop-filter: blur(20px);
            transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .toast.show {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }

        /* حالت خالی و لودینگ */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-sub);
        }

        .empty-icon {
            font-size: 2.8rem;
            margin-bottom: 12px;
            opacity: 0.8;
        }

        .loading-spinner {
            display: inline-block;
            width: 34px;
            height: 34px;
            border: 3px solid rgba(245, 158, 11, 0.2);
            border-radius: 50%;
            border-top-color: var(--gold-primary);
            animation: spin 0.75s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .tab-content { display: none; }
        .tab-content.active { display: block; animation: fadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1); }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* مودال‌های شیشه‌ای لوکس */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(4, 7, 13, 0.82);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            z-index: 300;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.28s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .modal-overlay.active {
            opacity: 1;
            pointer-events: auto;
        }

        .modal-card {
            background: linear-gradient(145deg, rgba(20, 27, 44, 0.96), rgba(11, 16, 28, 0.98));
            border: 1px solid rgba(255, 255, 255, 0.12);
            border-radius: var(--radius-lg);
            width: 100%;
            max-width: 440px;
            padding: 24px;
            box-shadow: 0 25px 60px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255, 255, 255, 0.15);
            transform: scale(0.92) translateY(12px);
            transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
            position: relative;
        }

        .modal-overlay.active .modal-card {
            transform: scale(1) translateY(0);
        }

        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 18px;
            border-bottom: 1px solid var(--border-glass);
            padding-bottom: 12px;
        }

        .modal-title {
            font-size: 1.08rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .modal-close-btn {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-glass);
            color: var(--text-sub);
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 1.1rem;
            transition: all 0.2s;
        }

        .modal-close-btn:active {
            transform: scale(0.9);
            color: var(--rose-main);
        }
    </style>
</head>
<body>

    <!-- کانواس آتش‌بازی و انیمیشن جشن -->
    <canvas id="confettiCanvas"></canvas>

    <!-- هدر بالای صفحه -->
    <header class="app-header">
        <div class="brand-box">
            <div class="brand-icon-box">☕</div>
            <div>
                <div class="brand-title">کافه دنگ</div>
                <div class="brand-subtitle">پارتنر حساب و کتاب دورهمی</div>
            </div>
        </div>
        <div class="user-pill" id="userPill" onclick="openProfileModal()">
            <span class="avatar-glow-dot"></span>
            <span id="userNameHeader">در حال اتصال...</span>
        </div>
    </header>

    <!-- کانتینر اصلی محتوا -->
    <main class="container">

        <!-- تب ۱: داشبورد من -->
        <section id="tab-dashboard" class="tab-content active">
            <!-- مسترکارت وضعیت مالی لوکس -->
            <div class="hero-wallet-card">
                <div class="wallet-card-top">
                    <div>
                        <div class="hero-balance-label">تراز خالص حساب شما</div>
                        <div class="hero-balance-amount" id="statNetTotal">۰ تومان</div>
                    </div>
                    <div class="card-chip"></div>
                </div>

                <div class="balance-split-row">
                    <div class="split-item">
                        <span class="split-label">طلبکاری‌های شما 💚</span>
                        <span class="split-val green" id="statCreditor">۰ تومان</span>
                    </div>
                    <div class="split-item" style="border-right: 1px solid var(--border-glass); padding-right: 12px;">
                        <span class="split-label">بدهکاری‌های شما 🔴</span>
                        <span class="split-val red" id="statDebtor">۰ تومان</span>
                    </div>
                </div>
            </div>

            <!-- کارت جمله روز کافه‌ای -->
            <div class="quote-card">
                <div class="quote-header">☕ جرعه‌ای حس خوب کافه‌ای:</div>
                <div class="quote-text" id="dailyQuoteText">قهوه‌ت رو بنوش، نفس عمیق بکش؛ قشنگ‌ترین اتفاق‌ها همیشه بی‌خبر میان ✨</div>
            </div>

            <!-- کارت‌های بانکی من (Apple Wallet Style) -->
            <div class="card">
                <div class="card-header">
                    <div class="card-title">💳 شماره کارت‌های من</div>
                    <button class="copy-btn" onclick="openAddCardModal()">➕ ثبت کارت جدید</button>
                </div>
                <div id="cardsListContainer">
                    <div class="empty-state">
                        <div class="loading-spinner"></div>
                        <p style="margin-top:12px;">در حال بارگذاری اطلاعات...</p>
                    </div>
                </div>
            </div>

            <!-- میانبرهای سریع و تعاملی -->
            <div class="card">
                <div class="card-title" style="margin-bottom:14px;">⚡ دسترسی‌های سریع</div>
                <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:10px;">
                    <button class="copy-btn" style="padding:14px 8px; justify-content:center; font-size:0.85rem;" onclick="switchTab('add-expense')">💸 ثبت هزینه</button>
                    <button class="copy-btn" style="padding:14px 8px; justify-content:center; font-size:0.85rem;" onclick="switchTab('shopping')">🛒 فاکتور خرید</button>
                    <button class="copy-btn" style="padding:14px 8px; justify-content:center; font-size:0.85rem;" onclick="switchTab('food')">🍕 گردونه غذا</button>
                </div>
            </div>
        </section>

        <!-- تب ۲: گروه‌ها و دنگ‌ها -->
        <section id="tab-groups" class="tab-content">
            <!-- چیپ‌های اسکرول گروه‌ها -->
            <div class="groups-scroll" id="groupsChipsContainer">
                <!-- دکمه‌های گروه‌ها -->
            </div>

            <div id="activeGroupDetailCard">
                <!-- اطلاعات تفصیلی گروه انتخاب شده -->
            </div>
        </section>

        <!-- تب ۳: ثبت سریع هزینه -->
        <section id="tab-add-expense" class="tab-content">
            <div class="card">
                <div class="card-title" style="margin-bottom:16px;">💸 ثبت سریع و آنلاین هزینه</div>
                
                <div class="form-group">
                    <label class="form-label">گروه مورد نظر:</label>
                    <select id="expenseGroupSelect" class="form-control" onchange="onExpenseGroupChange()">
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
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                        <div>
                            <label class="form-label">قیمت هر واحد (تومان):</label>
                            <input type="number" id="expenseUnitPriceInput" class="form-control" placeholder="35000" oninput="calcQtyTotal()">
                        </div>
                        <div>
                            <label class="form-label">تعداد یا مقدار:</label>
                            <input type="number" id="expenseQuantityInput" class="form-control" placeholder="4" step="0.5" oninput="calcQtyTotal()">
                        </div>
                    </div>
                    <div style="background:var(--bg-inner); border:1px solid var(--border-glass); border-radius:var(--radius-md); padding:12px 16px; display:flex; justify-content:space-between; margin-bottom:16px;">
                        <span style="color:var(--text-sub); font-size:0.88rem;">مبلغ کل محاسبه‌شده:</span>
                        <strong id="qtyCalculatedTotal" style="color:var(--gold-primary); font-size:1.05rem;">۰ تومان</strong>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label">پرداخت‌کننده (کی حساب کرده؟):</label>
                    <select id="expensePayerSelect" class="form-control">
                    </select>
                </div>

                <div class="form-group">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:8px;">
                        <label class="form-label" style="margin:0;">کسانی که در دنگ سهیم هستند:</label>
                        <span style="font-size:0.78rem; color:var(--gold-primary); cursor:pointer; font-weight:700;" onclick="toggleAllExpenseMembers()">انتخاب / لغو همه</span>
                    </div>
                    <div class="members-checklist" id="expenseMembersChecklist">
                    </div>
                </div>

                <div style="background:var(--bg-inner); border:1px solid var(--border-glass); border-radius:var(--radius-md); padding:14px 16px; display:flex; justify-content:space-between; margin-bottom:18px;">
                    <span style="color:var(--text-sub); font-size:0.9rem;">سهم هر نفر:</span>
                    <strong id="previewPerShare" style="color:var(--emerald-main); font-size:1.1rem;">۰ تومان</strong>
                </div>

                <button class="btn-primary" onclick="submitNewExpense()">
                    <span>✅ ثبت نهایی هزینه</span>
                </button>
            </div>
        </section>

        <!-- تب ۴: خریدهای خونه و مایحتاج -->
        <section id="tab-shopping" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <div>
                        <div class="card-title">🛒 خریدهای خونه و مایحتاج</div>
                        <div style="font-size:0.76rem; color:var(--text-sub); margin-top:2px;">افزودن نیازها، انتخاب اقلام خریداری‌شده و ثبت دنگ</div>
                    </div>
                    <select id="shoppingGroupSelect" class="form-control" style="width:auto; padding:6px 14px; font-size:0.86rem;" onchange="renderShoppingList()">
                    </select>
                </div>

                <!-- فرم افزودن سریع قلم به لیست خریدهای خونه -->
                <div style="background:var(--bg-inner); border:1px solid var(--border-glass); border-radius:var(--radius-md); padding:16px; margin-bottom:18px;">
                    <div style="font-size:0.92rem; font-weight:800; margin-bottom:12px; color:var(--gold-primary);">➕ افزودن نیاز جدید به لیست خرید:</div>
                    <div class="form-group" style="margin-bottom:10px;">
                        <input type="text" id="shopItemName" class="form-control" placeholder="نام کالا (مثلاً: شیر، روغن، نان، تخم‌مرغ)">
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px;">
                        <input type="number" id="shopItemQuantity" class="form-control" placeholder="تعداد یا کیلو (پیش‌فرض: ۱)" step="0.5" value="1" oninput="calcShopPreview()">
                        <input type="number" id="shopItemUnitPrice" class="form-control" placeholder="قیمت واحد (اختیاری)" oninput="calcShopPreview()">
                    </div>
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; font-size:0.84rem;">
                        <span style="color:var(--text-sub);">وضعیت قیمت:</span>
                        <strong id="shopItemTotalPreview" style="color:var(--gold-primary); font-size:0.92rem;">بدون قیمت (تعیین موقع خرید)</strong>
                    </div>
                    <button class="btn-primary" style="padding:12px;" onclick="submitNewShoppingItem()">
                        <span>➕ افزودن به لیست خریدهای خونه</span>
                    </button>
                </div>

                <!-- لیست اقلام فاکتور -->
                <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:12px;">
                    <span style="font-size:0.88rem; font-weight:800; color:var(--text-main);">📋 اقلام موجود در لیست:</span>
                    <button class="copy-btn" style="padding:4px 10px; font-size:0.75rem;" onclick="toggleAllShoppingCheckboxes()">انتخاب همه</button>
                </div>
                <div id="shoppingItemsContainer">
                </div>

                <!-- دکمه خرید و تسویه اقلام انتخاب شده -->
                <div style="margin-top:16px;">
                    <button class="btn-primary" id="btnSettleShopping" style="background:linear-gradient(135deg, #10b981 0%, #059669 100%); box-shadow:0 6px 20px rgba(16,185,129,0.3); display:none;" onclick="openSettleShoppingModal()">
                        <span>🛍️ من خریدم / ثبت دنگ اقلام انتخابی (<span id="selectedShopCountBadge">۰</span>)</span>
                    </button>
                </div>

                <!-- جمع کل فاکتور اقلام قیمت‌دار -->
                <div style="background:var(--bg-inner); border:1px solid var(--border-glass); border-radius:var(--radius-md); padding:14px 16px; display:flex; justify-content:space-between; margin-top:16px;">
                    <span style="color:var(--text-sub); font-size:0.88rem;">جمع اقلام قیمت‌دار:</span>
                    <strong id="shoppingGrandTotal" style="color:var(--emerald-main); font-size:1.1rem;">۰ تومان</strong>
                </div>
            </div>
        </section>

        <!-- تب ۵: گردونه غذا -->
        <section id="tab-food" class="tab-content">
            <div class="card wheel-container">
                <div class="card-title" style="justify-content:center; margin-bottom:8px;">🍕 چی بخوریم؟ (گردونه شانس دورهمی)</div>
                <p style="font-size:0.84rem; color:var(--text-sub); margin-bottom:18px;">
                    نمی‌دونید چی سفارش بدید؟ بذارید کافه دنگ رندوم براتون انتخاب کنه! 😋
                </p>

                <div class="segmented-control" style="margin-bottom:18px;">
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

                <button class="btn-primary" id="spinFoodBtn" onclick="spinFoodWheel()" style="margin-bottom:16px;">
                    <span>🎲 بچرخون و انتخاب کن!</span>
                </button>

                <!-- فرم افزودن غذای دلخواه جدید به گردونه -->
                <div style="background:var(--bg-inner); border:1px solid var(--border-glass); border-radius:var(--radius-md); padding:18px; margin-top:18px; text-align:right;">
                    <div style="font-size:0.94rem; font-weight:800; margin-bottom:12px; color:var(--gold-primary); display:flex; align-items:center; gap:8px;">
                        <span>➕ افزودن غذای دلخواه به گزینه‌ها:</span>
                    </div>
                    <div class="form-group" style="margin-bottom:12px;">
                        <input type="text" id="customFoodInput" class="form-control" placeholder="نام غذا (مثلاً: پاستا آلفردو، ساندویچ بندری، دیزی...)">
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:14px;">
                        <div>
                            <label class="form-label" style="font-size:0.78rem;">دسته‌بندی:</label>
                            <select id="customFoodCatSelect" class="form-control" style="padding:9px 12px; font-size:0.86rem;">
                                <option value="fastfood">فست‌فود 🍔</option>
                                <option value="traditional">سنتی و خوراک 🍢</option>
                                <option value="cafe">کافه و دسر ☕</option>
                                <option value="custom">دست‌ساز و خودمونی 🍳</option>
                            </select>
                        </div>
                        <div>
                            <label class="form-label" style="font-size:0.78rem;">ایموجی یا آیکون:</label>
                            <select id="customFoodEmojiSelect" class="form-control" style="padding:9px 12px; font-size:0.86rem;">
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
                    <button class="btn-primary" style="padding:12px; font-size:0.92rem;" onclick="submitNewCustomFood()">
                        <span>➕ ثبت و اضافه به گردونه</span>
                    </button>

                    <!-- لیست غذاهای اضافه شده -->
                    <div style="margin-top:18px;">
                        <div style="font-size:0.84rem; font-weight:800; color:var(--text-sub); margin-bottom:10px;">
                            📋 غذاهای اضافه شده توسط شما و گروه:
                        </div>
                        <div id="customFoodsListContainer">
                        </div>
                    </div>
                </div>
            </div>
        </section>

    </main>

    <!-- نوار ناوبری شناور و شیشه‌ای پایین (Floating Glass Dock) -->
    <div class="floating-dock-wrapper">
        <nav class="bottom-dock">
            <button class="nav-dock-btn active" id="btn-dashboard" onclick="switchTab('dashboard')">
                <span class="nav-icon">🏠</span>
                <span>داشبورد</span>
            </button>
            <button class="nav-dock-btn" id="btn-groups" onclick="switchTab('groups')">
                <span class="nav-icon">👥</span>
                <span>گروه‌ها</span>
            </button>
            <button class="nav-dock-btn" id="btn-add-expense" onclick="switchTab('add-expense')">
                <span class="nav-icon">➕</span>
                <span>ثبت هزینه</span>
            </button>
            <button class="nav-dock-btn" id="btn-shopping" onclick="switchTab('shopping')">
                <span class="nav-icon">🛒</span>
                <span>خرید</span>
            </button>
            <button class="nav-dock-btn" id="btn-food" onclick="switchTab('food')">
                <span class="nav-icon">🍕</span>
                <span>چی بخوریم</span>
            </button>
        </nav>
    </div>

    <!-- توست پیام موقت -->
    <div class="toast" id="toastMessage">
        <span>✨</span>
        <span id="toastText">عملیات با موفقیت انجام شد</span>
    </div>

    <!-- مودال اختصاصی ۱: پروفایل کاربری من -->
    <div class="modal-overlay" id="profileModal" onclick="closeModalOnBg(event, 'profileModal')">
        <div class="modal-card">
            <div class="modal-header">
                <div class="modal-title">
                    <span>👤</span>
                    <span>پروفایل کاربری من</span>
                </div>
                <button class="modal-close-btn" onclick="closeProfileModal()">✕</button>
            </div>
            
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="width: 68px; height: 68px; border-radius: 50%; background: linear-gradient(135deg, #f59e0b, #d97706); margin: 0 auto 12px; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; box-shadow: 0 0 25px var(--gold-glow); border: 2px solid rgba(255,255,255,0.2);" id="profileAvatarIcon">
                    ☕
                </div>
                <div style="font-size: 1.25rem; font-weight: 900; color: #ffffff;" id="profileModalName">کاربر گرامی</div>
                <div style="font-size: 0.82rem; color: var(--gold-primary); font-weight: 700; margin-top: 4px;" id="profileModalUsername">@username</div>
                <div style="display: inline-flex; align-items: center; gap: 6px; background: rgba(16, 185, 129, 0.12); border: 1px solid var(--emerald-main); color: var(--emerald-main); padding: 4px 12px; border-radius: var(--radius-full); font-size: 0.74rem; font-weight: 700; margin-top: 10px;">
                    <span style="width: 7px; height: 7px; background: var(--emerald-main); border-radius: 50%;"></span>
                    <span>متصل به حساب تلگرام (احراز هویت شده)</span>
                </div>
            </div>

            <div style="background: var(--bg-inner); border: 1px solid var(--border-glass); border-radius: var(--radius-md); padding: 14px; margin-bottom: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 0.86rem;">
                    <span style="color: var(--text-sub);">🆔 شناسه کاربری تلگرام:</span>
                    <span style="font-family: monospace; font-weight: 800; color: #ffffff;" id="profileModalId">-</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 0.86rem;">
                    <span style="color: var(--text-sub);">💳 کارت‌های بانکی ثبت‌شده:</span>
                    <span style="font-weight: 800; color: var(--gold-primary);" id="profileModalCardsCount">۰ کارت</span>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 7px 0; font-size: 0.86rem;">
                    <span style="color: var(--text-sub);">📁 گروه‌های مشترک من:</span>
                    <span style="font-weight: 800; color: #ffffff;" id="profileModalGroupsCount">۰ گروه</span>
                </div>
            </div>

            <div style="font-size: 0.76rem; color: var(--text-muted); text-align: center; margin-bottom: 18px; line-height: 1.6;">
                🔒 حساب و اطلاعات مالی شما کاملاً اختصاصی و ایمن است و هیچ کاربر دیگری به پنل شما دسترسی ندارد.
            </div>

            <button class="btn-primary" onclick="closeProfileModal()">
                <span>متوجه شدم ✨</span>
            </button>
        </div>
    </div>

    <!-- مودال اختصاصی ۲: ثبت کارت بانکی جدید -->
    <div class="modal-overlay" id="addCardModal" onclick="closeModalOnBg(event, 'addCardModal')">
        <div class="modal-card">
            <div class="modal-header">
                <div class="modal-title">
                    <span>💳</span>
                    <span>ثبت شماره کارت جدید</span>
                </div>
                <button class="modal-close-btn" onclick="closeAddCardModal()">✕</button>
            </div>
            
            <div class="form-group">
                <label class="form-label">شماره ۱۶ رقمی کارت بانکی:</label>
                <input type="tel" id="newCardNumberInput" class="form-control" style="font-family: monospace; direction: ltr; font-size: 1.15rem; letter-spacing: 2px; text-align: center;" placeholder="6037 9911 2233 4455" maxlength="19" oninput="onCardNumberChange(this)">
            </div>

            <div class="form-group">
                <label class="form-label">نام بانک (شناسایی خودکار):</label>
                <div style="position: relative;">
                    <input type="text" id="newCardBankNameInput" class="form-control" placeholder="مثال: بانک ملی یا سامان">
                    <span id="detectedBankBadge" style="position: absolute; left: 12px; top: 50%; transform: translateY(-50%); font-size: 0.76rem; color: var(--gold-primary); font-weight: 800;"></span>
                </div>
            </div>

            <div style="display: flex; gap: 10px; margin-top: 22px;">
                <button class="btn-primary" style="flex: 2;" onclick="submitNewCard()">
                    <span>💾 ثبت و ذخیره کارت</span>
                </button>
                <button class="del-btn" style="flex: 1; height: auto; border-radius: var(--radius-md); font-weight: 700; background: rgba(255,255,255,0.06); border-color: var(--border-glass); color: var(--text-sub);" onclick="closeAddCardModal()">
                    <span>انصراف</span>
                </button>
            </div>
        </div>
    </div>

    <!-- مودال اختصاصی ۳: ثبت مبالغ و محاسبه دنگ خریدهای خونه -->
    <div class="modal-overlay" id="settleShoppingModal" onclick="closeModalOnBg(event, 'settleShoppingModal')">
        <div class="modal-card">
            <div class="modal-header">
                <div class="modal-title">
                    <span>🛍️</span>
                    <span>ثبت مبالغ و محاسبه دنگ خرید</span>
                </div>
                <button class="modal-close-btn" onclick="closeSettleShoppingModal()">✕</button>
            </div>
            
            <p style="font-size:0.82rem; color:var(--text-sub); margin-bottom:14px; line-height:1.6;">
                مبلغ پرداختی برای هر قلم خریداری‌شده را به تومان وارد کنید تا دنگ آن بین اعضای گروه تقسیم و ثبت شود:
            </p>

            <div id="settleShoppingItemsList" style="max-height:220px; overflow-y:auto; margin-bottom:16px; display:flex; flex-direction:column; gap:10px;">
            </div>

            <div style="background:var(--bg-inner); border:1px solid var(--border-glass); border-radius:var(--radius-md); padding:12px; margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">
                <span style="color:var(--text-sub); font-size:0.88rem;">💳 مجموع کل فاکتور:</span>
                <strong id="settleShoppingGrandTotal" style="color:var(--emerald-main); font-size:1.15rem;">۰ تومان</strong>
            </div>

            <div style="display:flex; gap:10px;">
                <button class="btn-primary" style="flex:2;" onclick="submitSettleShopping()">
                    <span>💾 ثبت دنگ در گروه ✨</span>
                </button>
                <button class="del-btn" style="flex:1; height:auto; border-radius:var(--radius-md); font-weight:700; background:rgba(255,255,255,0.06); border-color:var(--border-glass); color:var(--text-sub);" onclick="closeSettleShoppingModal()">
                    <span>انصراف</span>
                </button>
            </div>
        </div>
    </div>

    <script>
        // اتصال به تلگرام وب‌اپ
        const tg = window.Telegram?.WebApp;
        if (tg) {
            try {
                tg.ready();
                tg.expand();
                if (tg.setHeaderColor) tg.setHeaderColor('#080c14');
                if (tg.setBackgroundColor) tg.setBackgroundColor('#080c14');
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
            selectedFoodCategory: 'all',
            customFoods: []
        };

        // فهرست پیش‌فرض غذاهای کافه دنگ
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

        // عدد فرمت شده به تومان
        function formatToman(num) {
            if (num === null || num === undefined) return "۰ تومان";
            return Number(num).toLocaleString('fa-IR') + " تومان";
        }

        // نمایش Toast شناور
        function showToast(text) {
            const toast = document.getElementById('toastMessage');
            document.getElementById('toastText').innerText = text;
            toast.classList.add('show');
            if (tg?.HapticFeedback) {
                tg.HapticFeedback.notificationOccurred('success');
            }
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2600);
        }

        // کپی متن با Toast
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
            document.querySelectorAll('.nav-dock-btn').forEach(el => el.classList.remove('active'));
            
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
                if (tg?.initDataUnsafe?.user?.id) {
                    appState.userId = tg.initDataUnsafe.user.id;
                    url += '?user_id=' + appState.userId;
                } else if (appState.userId) {
                    url += '?user_id=' + appState.userId;
                }

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

                renderDashboard(data);
                renderCustomFoodsList();

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
                netEl.innerText = '+' + formatToman(stats.net_total);
                netEl.style.color = 'var(--emerald-main)';
            } else if (stats.net_total < 0) {
                netEl.innerText = formatToman(stats.net_total);
                netEl.style.color = 'var(--rose-main)';
            } else {
                netEl.innerText = 'بی‌حساب و صاف ✨';
                netEl.style.color = 'var(--gold-primary)';
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
                            <div class="bank-card-top">
                                <div class="bank-name-badge">
                                    <span>🏦</span>
                                    <span>${c.bank_name || 'بانک'}</span>
                                </div>
                                ${c.is_default ? '<span style="font-size:0.75rem; color:#fef08a; font-weight:700;">★ کارت اصلی</span>' : ''}
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
                        <button class="copy-btn" style="margin-top:10px;" onclick="openAddCardModal()">➕ ثبت اولین کارت</button>
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

            // چیپ‌های انتخاب گروه
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

            const currentGroup = data.groups.find(g => g.id === appState.currentGroupId) || data.groups[0];
            if (!currentGroup) return;

            let groupHtml = `
                <div class="card">
                    <div class="card-header">
                        <div>
                            <div class="card-title">🏕️ ${currentGroup.title}</div>
                            <div style="font-size:0.78rem; color:var(--text-sub); margin-top:3px;">
                                ${currentGroup.members.length} عضو • کد دعوت: <code style="color:var(--gold-primary); font-weight:700;">${currentGroup.invite_code}</code>
                            </div>
                        </div>
                        <button class="copy-btn" onclick="copyInviteLink('${currentGroup.invite_code}')">💌 لینک دعوت</button>
                    </div>

                    <!-- بخش تسویه حساب بدهی‌ها -->
                    <div style="margin-top:18px;">
                        <div style="font-size:0.94rem; font-weight:800; margin-bottom:12px; color:var(--gold-primary);">
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
                        <div class="item-row" style="flex-direction:column; align-items:stretch; gap:12px; padding:16px; margin-bottom:12px;">
                            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;">
                                <div style="font-size:0.98rem; font-weight:800;">
                                    <span style="color:var(--rose-main);">${fromName}</span>
                                    <span style="color:var(--text-sub); font-size:0.84rem; margin:0 6px;">بدهد به ➔</span>
                                    <span style="color:var(--emerald-main);">${toName}</span>
                                </div>
                                <div class="item-price" style="font-size:1.1rem;">${formatToman(s.amount)}</div>
                            </div>
                            ${toUserCard ? `
                                <div style="display:flex; align-items:center; justify-content:space-between; background:rgba(8,12,20,0.7); padding:10px 14px; border-radius:var(--radius-md); border:1px solid var(--border-glass);">
                                    <div style="font-size:0.82rem; color:var(--text-sub); display:flex; align-items:center; gap:8px;">
                                        <span>💳 شماره کارت:</span>
                                        <span style="font-family:monospace; direction:ltr; unicode-bidi:embed; font-size:0.98rem; color:#ffffff; font-weight:800; letter-spacing:1.5px;">${toUserCardFormatted}</span>
                                    </div>
                                    <button class="copy-btn" onclick="copyText('${toUserCard}', 'شماره کارت')">کپی کارت</button>
                                </div>
                            ` : `
                                <div style="font-size:0.78rem; color:var(--text-muted);">
                                    (شماره کارت طلبکار هنوز ثبت نشده است)
                                </div>
                            `}
                        </div>
                    `;
                });
            } else {
                groupHtml += `
                    <div style="background:var(--bg-inner); border:1px solid var(--border-glass); border-radius:var(--radius-md); padding:14px; text-align:center; color:var(--emerald-main); font-size:0.9rem; font-weight:700;">
                        ✨ تمام حساب‌ها در این گروه صاف و تسویه است!
                    </div>
                `;
            }

            // لیست آخرین هزینه‌ها
            groupHtml += `
                    <div style="margin-top:22px;">
                        <div style="font-size:0.94rem; font-weight:800; margin-bottom:10px; color:var(--gold-primary);">
                            💸 هزینه‌های اخیر گروه:
                        </div>
            `;

            const expenses = currentGroup.expenses || [];
            if (expenses.length > 0) {
                expenses.forEach(e => {
                    groupHtml += `
                        <div class="item-row">
                            <div style="display:flex; flex-direction:column; gap:2px;">
                                <div style="font-size:0.94rem; font-weight:800;">${e.title}</div>
                                <div style="font-size:0.78rem; color:var(--text-sub);">پرداخت‌کننده: <strong>${e.payer_name}</strong></div>
                            </div>
                            <div class="item-price">${formatToman(e.amount)}</div>
                        </div>
                    `;
                });
            } else {
                groupHtml += `
                    <div style="background:var(--bg-inner); border:1px solid var(--border-glass); border-radius:var(--radius-md); padding:14px; text-align:center; color:var(--text-sub); font-size:0.86rem;">
                        هنوز هزینه‌ای در این دوره ثبت نشده است.
                    </div>
                `;
            }

            // لیست اعضا و تراز فردی
            groupHtml += `
                    <div style="margin-top:22px;">
                        <div style="font-size:0.94rem; font-weight:800; margin-bottom:10px; color:var(--gold-primary);">
                            👥 وضعیت اعضا و دنگ‌ها:
                        </div>
            `;

            const memberStats = currentGroup.balances?.member_stats || [];
            memberStats.forEach(m => {
                const net = m.net || 0;
                let netText = '۰';
                let netColor = 'var(--gold-primary)';
                if (net > 0) {
                    netText = '+' + formatToman(net);
                    netColor = 'var(--emerald-main)';
                } else if (net < 0) {
                    netText = formatToman(net);
                    netColor = 'var(--rose-main)';
                }

                groupHtml += `
                    <div class="item-row">
                        <div style="display:flex; flex-direction:column; gap:2px;">
                            <div style="font-size:0.94rem; font-weight:800;">${m.user?.display_name || m.user?.full_name || 'عضو'}</div>
                            <div style="font-size:0.78rem; color:var(--text-sub);">پرداختی: ${formatToman(m.paid)} | سهم: ${formatToman(m.owed)}</div>
                        </div>
                        <div style="font-size:0.98rem; font-weight:800; color:${netColor};">${netText}</div>
                    </div>
                `;
            });

            groupHtml += `
                    </div>
                </div>
            `;

            document.getElementById('activeGroupDetailCard').innerHTML = groupHtml;
        }

        function selectGroup(groupId) {
            appState.currentGroupId = groupId;
            renderGroupsTab();
        }

        function copyInviteLink(code) {
            const botUsername = 'dong_yar_bot';
            const link = 'https://t.me/' + botUsername + '?start=join_' + code;
            copyText(link, 'لینک دعوت به گروه');
        }

        function prepareExpenseForm() {
            const data = appState.userData;
            if (!data || !data.groups || data.groups.length === 0) return;

            const grpSelect = document.getElementById('expenseGroupSelect');
            grpSelect.innerHTML = data.groups.map(g => `<option value="${g.id}" ${g.id === appState.currentGroupId ? 'selected' : ''}>${g.title}</option>`).join('');
            
            onExpenseGroupChange();
        }

        function onExpenseGroupChange() {
            const groupId = parseInt(document.getElementById('expenseGroupSelect').value);
            const group = appState.userData.groups.find(g => g.id === groupId);
            if (!group) return;

            const payerSelect = document.getElementById('expensePayerSelect');
            payerSelect.innerHTML = group.members.map(m => `
                <option value="${m.id}" ${m.id === appState.userId ? 'selected' : ''}>
                    ${m.display_name || m.full_name}
                </option>
            `).join('');

            const checklist = document.getElementById('expenseMembersChecklist');
            checklist.innerHTML = group.members.map(m => `
                <label class="member-checkbox-label">
                    <input type="checkbox" class="exp-member-cb" value="${m.id}" checked onchange="updateSharePreview()">
                    <span>${m.display_name || m.full_name}</span>
                </label>
            `).join('');

            updateSharePreview();
        }

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

        function calcQtyTotal() {
            const unit = parseFloat(document.getElementById('expenseUnitPriceInput').value) || 0;
            const qty = parseFloat(document.getElementById('expenseQuantityInput').value) || 0;
            const total = Math.round(unit * qty);
            document.getElementById('qtyCalculatedTotal').innerText = formatToman(total);
            updateSharePreview();
        }

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
                    triggerConfetti();
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

        // فاکتور و لیست خریدهای خونه
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
                const btn = document.getElementById('btnSettleShopping');
                if (btn) btn.style.display = 'none';
                return;
            }

            let html = '';
            let total = 0;
            group.shopping_items.forEach(item => {
                total += (item.total_price || 0);
                const hasPrice = (item.total_price || 0) > 0;
                html += `
                    <div class="item-row" style="gap:10px;">
                        <div style="display:flex; align-items:center; gap:12px; flex:1;">
                            <input type="checkbox" class="shop-item-cb" value="${item.id}" data-id="${item.id}" data-name="${item.item_name}" data-price="${item.total_price || 0}" data-qty="${item.quantity || 1}" onchange="onShopItemCheckChange()" style="width:18px; height:18px; accent-color:var(--gold-primary); cursor:pointer;">
                            <div style="display:flex; flex-direction:column; gap:2px;">
                                <div style="font-size:0.94rem; font-weight:800;">${item.item_name}</div>
                                <div style="font-size:0.76rem; color:var(--text-sub);">
                                    مقدار: ${item.quantity || 1} ${hasPrice ? '• فی: ' + formatToman(item.unit_price) : ''}
                                </div>
                            </div>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <div class="item-price" style="font-size:0.92rem;">
                                ${hasPrice ? formatToman(item.total_price) : '<span style="color:var(--gold-primary); font-size:0.75rem; font-weight:700;">📌 نیاز به خرید</span>'}
                            </div>
                            <button class="del-btn" onclick="deleteShoppingItem(${item.id}, ${currentGroupId})">✕</button>
                        </div>
                    </div>
                `;
            });

            container.innerHTML = html;
            document.getElementById('shoppingGrandTotal').innerText = formatToman(total);
            onShopItemCheckChange();
        }

        function onShopItemCheckChange() {
            const checked = document.querySelectorAll('.shop-item-cb:checked');
            const count = checked.length;
            const btn = document.getElementById('btnSettleShopping');
            if (btn) {
                if (count > 0) {
                    btn.style.display = 'flex';
                    const badge = document.getElementById('selectedShopCountBadge');
                    if (badge) badge.innerText = count;
                } else {
                    btn.style.display = 'none';
                }
            }
        }

        function toggleAllShoppingCheckboxes() {
            const cbs = document.querySelectorAll('.shop-item-cb');
            const allChecked = Array.from(cbs).every(cb => cb.checked);
            cbs.forEach(cb => cb.checked = !allChecked);
            onShopItemCheckChange();
        }

        function calcShopPreview() {
            const p = parseFloat(document.getElementById('shopItemUnitPrice').value) || 0;
            const q = parseFloat(document.getElementById('shopItemQuantity').value) || 1;
            if (p > 0) {
                document.getElementById('shopItemTotalPreview').innerText = formatToman(Math.round(p * q));
            } else {
                document.getElementById('shopItemTotalPreview').innerText = 'بدون قیمت (تعیین موقع خرید)';
            }
        }

        async function submitNewShoppingItem() {
            const groupId = parseInt(document.getElementById('shoppingGroupSelect').value);
            const name = document.getElementById('shopItemName').value.trim();
            const unitPrice = parseInt(document.getElementById('shopItemUnitPrice').value) || 0;
            const quantity = parseFloat(document.getElementById('shopItemQuantity').value) || 1;

            if (!name) {
                showToast('لطفاً نام کالا را بنویسید');
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
                    showToast('قلم به لیست خریدهای خونه اضافه شد 🛒✨');
                    document.getElementById('shopItemName').value = '';
                    document.getElementById('shopItemUnitPrice').value = '';
                    document.getElementById('shopItemQuantity').value = '1';
                    calcShopPreview();
                    await loadData();
                    renderShoppingList();
                }
            } catch (e) {
                showToast('خطا در ثبت قلم خرید');
            }
        }

        // مودال تسویه اقلام خریداری‌شده
        function openSettleShoppingModal() {
            const checked = Array.from(document.querySelectorAll('.shop-item-cb:checked'));
            if (checked.length === 0) return;

            let html = '';
            checked.forEach((cb) => {
                const id = cb.value;
                const name = cb.dataset.name;
                const initialPrice = parseInt(cb.dataset.price) || '';
                html += `
                    <div style="background:var(--bg-card); border:1px solid var(--border-glass); border-radius:var(--radius-md); padding:10px 14px; display:flex; align-items:center; justify-content:space-between; gap:10px;">
                        <span style="font-size:0.9rem; font-weight:800; flex:1;">${name}</span>
                        <input type="number" class="form-control settle-item-price-input" data-id="${id}" data-name="${name}" placeholder="مبلغ خرید (تومان)" value="${initialPrice}" style="width:140px; padding:8px 12px; font-size:0.88rem;" oninput="calcSettleModalTotal()">
                    </div>
                `;
            });

            document.getElementById('settleShoppingItemsList').innerHTML = html;
            calcSettleModalTotal();
            document.getElementById('settleShoppingModal').classList.add('active');
            if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
        }

        function closeSettleShoppingModal() {
            document.getElementById('settleShoppingModal').classList.remove('active');
        }

        function calcSettleModalTotal() {
            const inputs = document.querySelectorAll('.settle-item-price-input');
            let total = 0;
            inputs.forEach(inp => {
                total += parseInt(inp.value) || 0;
            });
            document.getElementById('settleShoppingGrandTotal').innerText = formatToman(total);
            return total;
        }

        async function submitSettleShopping() {
            const total = calcSettleModalTotal();
            if (total <= 0) {
                showToast('⚠️ لطفاً مبلغ اقلام خریداری‌شده را وارد کنید');
                return;
            }

            const inputs = Array.from(document.querySelectorAll('.settle-item-price-input'));
            const itemNames = inputs.map(i => i.dataset.name).join('، ');
            const title = 'خرید خونه (' + itemNames.substring(0, 36) + ')';
            const groupId = parseInt(document.getElementById('shoppingGroupSelect').value);
            const group = appState.userData?.groups?.find(g => g.id === groupId);
            const members = group?.members || [{ id: appState.userId || 1 }];

            // تقسیم دنگ مساوی
            const baseShare = Math.floor(total / members.length);
            let rem = total - (baseShare * members.length);
            const shares = {};
            members.forEach(m => {
                shares[m.id] = baseShare + (rem > 0 ? 1 : 0);
                if (rem > 0) rem--;
            });

            try {
                // ثبت به عنوان هزینه گروه
                const expRes = await fetch('/api/app/add_expense', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        group_id: groupId,
                        payer_id: appState.userId || 1,
                        title: title,
                        amount: total,
                        shares: shares
                    })
                });
                const expData = await expRes.json();
                if (!expData.success) {
                    showToast('خطا در ثبت دنگ خرید');
                    return;
                }

                // حذف اقلام خریداری‌شده از لیست
                for (const inp of inputs) {
                    const itemId = parseInt(inp.dataset.id);
                    await fetch('/api/app/delete_shopping_item', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ item_id: itemId, group_id: groupId })
                    });
                }

                closeSettleShoppingModal();
                triggerConfetti();
                showToast('🎉 خرید با موفقیت ثبت شد و دنگ آن حساب گردید!');
                await loadData();
                renderShoppingList();
            } catch (err) {
                showToast('خطای شبکه در تسویه خرید');
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
                    showToast('قلم از لیست خرید حذف شد');
                    await loadData();
                    renderShoppingList();
                }
            } catch (e) {
                showToast('خطا در حذف قلم');
            }
        }

        // گردونه غذا و غذاهای اختصاصی
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
                container.innerHTML = '<div style="font-size:0.78rem; color:var(--text-muted); text-align:center; padding:10px;">هنوز غذای دلخواهی اضافه نشده است.</div>';
                return;
            }
            let html = '<div style="display:flex; flex-direction:column; gap:8px;">';
            list.forEach(f => {
                html += `
                    <div class="item-row" style="padding:10px 14px; margin-bottom:0; justify-content:space-between;">
                        <div style="display:flex; align-items:center; gap:10px;">
                            <span style="font-size:1.35rem;">${f.emoji || '🍽️'}</span>
                            <div style="text-align:right;">
                                <div style="font-size:0.92rem; font-weight:800;">${f.name}</div>
                                <div style="font-size:0.74rem; color:var(--text-sub);">${f.description || 'پیشنهاد اختصاصی شما ✨'}</div>
                            </div>
                        </div>
                        <button class="del-btn" style="width:28px; height:28px; font-size:0.8rem;" onclick="deleteCustomFood(${f.id})">✕</button>
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
                    triggerConfetti();
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
                    triggerConfetti();
                    if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
                }
            }, 80);
        }

        // افکت آتش‌بازی و کانواس جشن (Confetti)
        function triggerConfetti() {
            const canvas = document.getElementById('confettiCanvas');
            if (!canvas) return;
            const ctx = canvas.getContext('2d');
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;

            const particles = [];
            const colors = ['#f59e0b', '#10b981', '#38bdf8', '#f43f5e', '#fef08a'];

            for (let i = 0; i < 70; i++) {
                particles.push({
                    x: canvas.width / 2,
                    y: canvas.height / 2,
                    vx: (Math.random() - 0.5) * 14,
                    vy: (Math.random() - 0.5) * 14 - 3,
                    size: Math.random() * 7 + 4,
                    color: colors[Math.floor(Math.random() * colors.length)],
                    alpha: 1,
                    rotation: Math.random() * 360,
                    vRot: (Math.random() - 0.5) * 10
                });
            }

            let animationFrame;
            function render() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                let alive = false;
                particles.forEach(p => {
                    p.x += p.vx;
                    p.y += p.vy;
                    p.vy += 0.35; // گرانش
                    p.alpha -= 0.018;
                    p.rotation += p.vRot;

                    if (p.alpha > 0) {
                        alive = true;
                        ctx.save();
                        ctx.globalAlpha = p.alpha;
                        ctx.translate(p.x, p.y);
                        ctx.rotate(p.rotation * Math.PI / 180);
                        ctx.fillStyle = p.color;
                        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
                        ctx.restore();
                    }
                });

                if (alive) {
                    animationFrame = requestAnimationFrame(render);
                } else {
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    cancelAnimationFrame(animationFrame);
                }
            }
            render();
        }

        // مدیریت مودال پروفایل اختصاصی کاربر
        function openProfileModal() {
            const data = appState.userData;
            const user = data?.user || {};
            
            const displayName = user.calling_name || user.full_name || 'کاربر گرامی';
            const username = user.username ? ('@' + user.username) : 'بدون یوزرنیم تلگرام';
            const uid = user.id || appState.userId || '-';
            const cardsCount = (data?.cards || []).length;
            const groupsCount = (data?.groups || []).length;

            document.getElementById('profileModalName').innerText = displayName;
            document.getElementById('profileModalUsername').innerText = username;
            document.getElementById('profileModalId').innerText = uid;
            document.getElementById('profileModalCardsCount').innerText = cardsCount + ' کارت فعال';
            document.getElementById('profileModalGroupsCount').innerText = groupsCount + ' گروه دورهمی';

            const firstLetter = displayName.trim().charAt(0) || '☕';
            document.getElementById('profileAvatarIcon').innerText = firstLetter;

            document.getElementById('profileModal').classList.add('active');
            if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
        }

        function closeProfileModal() {
            document.getElementById('profileModal').classList.remove('active');
        }

        function closeModalOnBg(e, modalId) {
            if (e.target && e.target.id === modalId) {
                document.getElementById(modalId).classList.remove('active');
            }
        }

        // دیکشنری پیش‌شماره‌های بانکی ایران برای شناسایی خودکار کارت
        const IRAN_BANK_BINS = {
            "603799": "بانک ملی",
            "589210": "بانک سپه",
            "627648": "بانک صادرات",
            "627961": "بانک صنعت و معدن",
            "603770": "بانک کشاورزی",
            "628023": "بانک مسکن",
            "627760": "پست بانک",
            "502908": "بانک توسعه تعاون",
            "627412": "بانک اقتصاد نوین",
            "622106": "بانک پارسیان",
            "502229": "بانک پاسارگاد",
            "639607": "بانک سرمایه",
            "636214": "بانک آینده",
            "627381": "بانک انصار",
            "610433": "بانک ملت",
            "627353": "بانک تجارت",
            "505416": "بانک گردشگری",
            "505785": "بانک ایران زمین",
            "639346": "بانک سینا",
            "585983": "بانک تجارت",
            "863588": "بانک سامان",
            "621986": "بانک سامان",
            "505801": "بانک کوثر",
            "504706": "بانک شهر",
            "606373": "بلو بانک (Blu) / مهر ایران",
            "502938": "بانک دی",
            "504172": "بانک رسالت",
            "639599": "بانک قوامین",
            "636949": "بانک حکمت"
        };

        // باز و بسته کردن مودال ثبت کارت بانکی
        function openAddCardModal() {
            document.getElementById('newCardNumberInput').value = '';
            document.getElementById('newCardBankNameInput').value = '';
            document.getElementById('detectedBankBadge').innerText = '';
            document.getElementById('addCardModal').classList.add('active');
            if (tg?.HapticFeedback) tg.HapticFeedback.impactOccurred('light');
        }

        function closeAddCardModal() {
            document.getElementById('addCardModal').classList.remove('active');
        }

        function onCardNumberChange(input) {
            let digits = input.value.replace(/\D/g, '');
            if (digits.length > 16) digits = digits.substring(0, 16);
            
            // قالب‌بندی ۴ رقم ۴ رقم با فاصله
            const formatted = digits.replace(/(\d{4})/g, '$1 ').trim();
            input.value = formatted;

            // تشخیص هوشمند نام بانک
            if (digits.length >= 6) {
                const bin = digits.substring(0, 6);
                const bank = IRAN_BANK_BINS[bin];
                if (bank) {
                    const bankInput = document.getElementById('newCardBankNameInput');
                    bankInput.value = bank;
                    document.getElementById('detectedBankBadge').innerText = '✓ ' + bank;
                } else {
                    document.getElementById('detectedBankBadge').innerText = '';
                }
            } else {
                document.getElementById('detectedBankBadge').innerText = '';
            }
        }

        async function submitNewCard() {
            const raw = document.getElementById('newCardNumberInput').value;
            const digits = raw.replace(/\D/g, '');
            const bankName = document.getElementById('newCardBankNameInput').value.trim() || 'بانک';

            if (digits.length !== 16) {
                showToast('⚠️ شماره کارت باید ۱۶ رقم باشد');
                return;
            }

            try {
                const res = await fetch('/api/app/add_card', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        user_id: appState.userId || 1,
                        card_number: digits,
                        bank_name: bankName
                    })
                });
                const resData = await res.json();
                if (resData.success) {
                    closeAddCardModal();
                    triggerConfetti();
                    showToast('کارت بانکی با موفقیت ثبت شد 💳✨');
                    await loadData();
                } else {
                    showToast('خطا: شماره کارت نامعتبر است');
                }
            } catch (e) {
                showToast('خطا در ارتباط با سرور');
            }
        }

        // اجرای شروع اولیه
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
    """دریافت بسته کامل اطلاعات کاربر برای مینی‌اپ (پروفایل، گروه‌ها، ترازها، کارت‌ها، غذاها)"""
    try:
        user_id_param = request.query.get("user_id")
        user_id = int(user_id_param) if user_id_param and user_id_param.isdigit() else None

        async with aiosqlite.connect(DB_PATH) as conn:
            conn.row_factory = aiosqlite.Row
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
    """ثبت قلم جدید در فاکتور یا خریدهای خونه از طریق مینی‌اپ"""
    try:
        body = await request.json()
        group_id = int(body["group_id"])
        user_id = int(body["user_id"])
        item_name = str(body["item_name"]).strip()
        unit_price = int(body.get("unit_price", 0) or 0)
        quantity = float(body.get("quantity", 1) or 1)

        if not item_name or unit_price < 0:
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
