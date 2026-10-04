from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb

router = Router()

HELP_TEXT = """
💡 <b>راهنمای کار با ربات دنگ‌بگیر و حساب‌کشی</b>

این ربات به شما و دوستانتان کمک می‌کند هزینه‌های مشترک (سفر، هم‌خانه‌ای، کافه، پروژه‌ها و...) را به‌صورت کاملاً دقیق و خودکار مدیریت کنید:

<b>۱. ثبت کارت بانکی:</b>
از منوی اصلی گزینه <b>«💳 شماره کارت بانکی من»</b> را بزنید و شماره کارتتان را ثبت کنید تا در زمان تسویه، کارت شما به بدهکاران نمایش داده شود.

<b>۲. ساخت گروه و انتخاب لحن مکالمه:</b>
با زدن <b>«➕ ایجاد گروه جدید»</b> می‌توانید اسم رندوم خنده‌دار (+18) یا دلخواه بگذارید. همچنین از داخل گروه با دکمه <b>«🎭 تغییر لحن ربات»</b> می‌توانید لحن مکالمه را بین <b>رسمی</b>، <b>دوستانه</b> یا <b>بی‌ادب (+18)</b> تغییر دهید!

<b>۳. ثبت هزینه و سهم‌ها:</b>
با زدن <b>«💸 ثبت هزینه جدید»</b> عنوان و مبلغ خرج‌شده را وارد کرده و مشخص می‌کنید چه کسانی در این هزینه سهیم هستند.

<b>۴. فرمول تسویه و یادآوری واریز:</b>
در بخش <b>«⚖️ فرمول تسویه حساب»</b>، دقیقاً مشخص می‌شود چه کسی به کی چقدر بدهکار است. کنار هر بدهی:
• دکمه <b>«💸 اعلام واریز»</b> برای بدهکار قرار دارد تا به طلبکار پیام دهد پول را ریخته است.
• دکمه <b>«🔔 یادآوری»</b> برای طلبکار قرار دارد تا با لحن انتخابی گروه، به بدهکار اخطار و یادآوری واریز بفرستد!

<b>۵. صفر کردن حساب‌ها:</b>
با زدن <b>«🔄 صفر کردن حساب‌ها»</b> دوره مالی بسته شده و حساب‌ها برای خریدهای بعدی صفر می‌شوند.
"""

@router.message(CommandStart())
async def handle_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    user = message.from_user
    if not user:
        return
        
    await db.upsert_user(user.id, user.username, user.full_name)

    # بررسی پیوستن با لینک دعوت (Deep Linking)
    args = command.args
    if args and args.startswith("join_"):
        invite_code = args.replace("join_", "").strip()
        group = await db.get_group_by_code(invite_code)
        
        if group:
            added, nickname = await db.add_group_member(group["id"], user.id)
            members = await db.get_group_members(group["id"])
            if added:
                msg = (
                    f"🎉 شما با لقب اختصاصی <b>«{nickname}»</b> به گروه <b>«{group['title']}»</b> پیوستید! 🔞\n\n"
                    f"👥 تعداد اعضای گروه: {len(members)} نفر"
                )
            else:
                msg = (
                    f"ℹ️ شما هم‌اکنون با لقب <b>«{nickname}»</b> عضو گروه <b>«{group['title']}»</b> هستید.\n\n"
                    f"👥 تعداد اعضای گروه: {len(members)} نفر"
                )
            
            await message.answer(
                msg,
                parse_mode="HTML",
                reply_markup=kb.group_dashboard_keyboard(group["id"])
            )
            return
        else:
            await message.answer("⚠️ لینک دعوت نامعتبر است یا گروه منقضی شده است.")

    welcome_text = (
        f"سلام <b>{user.full_name}</b> عزیز، خیلی خوش اومدی! 🌺\n\n"
        "به ربات هوشمند محاسبه دنگ و حساب‌کشی خوش اومدی.\n"
        "با این ربات دیگه هیچ حسابی گم نمیشه و آخر هر سفر یا دورهمی، با کمترین تعداد تراکنش حساب‌ها صاف میشه!\n\n"
        "🎭 <b>امکان ویژه:</b> می‌تونی لحن ربات رو برای هر گروه بین <b>رسمی</b>، <b>دوستانه و خودمونی</b> یا <b>بی‌ادب و خفن (+18)</b> تنظیم کنی تا با هر سبکی که دوست دارید کل‌کل کنه و یادآوری بفرسته!\n\n"
        "برای شروع یکی از گزینه‌های زیر رو انتخاب کن:"
    )
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=kb.main_menu_keyboard()
    )


@router.message(Command("help"))
@router.callback_query(F.data == "nav:help")
async def handle_help(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    reply_markup = kb.InlineKeyboardMarkup(inline_keyboard=[
        [kb.InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main")]
    ])
    
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(HELP_TEXT, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await event.answer(HELP_TEXT, parse_mode="HTML", reply_markup=reply_markup)


@router.callback_query(F.data == "nav:main")
async def handle_nav_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    user = callback.from_user
    welcome_text = (
        f"سلام <b>{user.full_name}</b> عزیز! 🌺\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=kb.main_menu_keyboard()
    )


@router.message(Command("reset", "reset_all_data"))
async def handle_reset_prompt(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "⚠️ <b>هشدار پاکسازی و ریست کامل اطلاعات:</b>\n\n"
        "آیا مطمئن هستید که می‌خواهید <b>تمام داده‌های ربات</b> را پاک کنید؟\n"
        "• تمام گروه‌ها، اعضا، دنگ‌ها، هزینه‌ها و شماره کارت‌ها کاملاً پاک خواهند شد و ربات از صفر شروع به کار می‌کند."
    )
    markup = kb.InlineKeyboardMarkup(inline_keyboard=[
        [kb.InlineKeyboardButton(text="🔥 بله، تمام داده‌ها پاک شوند", callback_data="admin:reset:confirm")],
        [kb.InlineKeyboardButton(text="❌ انصراف", callback_data="nav:main")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "admin:reset:confirm")
async def handle_reset_execute(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await db.reset_all_database()
    await callback.answer("✅ تمام داده‌های ربات پاک شدند!", show_alert=True)
    
    text = (
        "🧹 <b>تمام داده‌های ربات با موفقیت پاکسازی و صفر شدند!</b>\n\n"
        "ربات به حالت اولیه و صفر بازگشت."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())

