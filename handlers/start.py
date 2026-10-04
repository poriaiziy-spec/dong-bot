from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb

router = Router()

HELP_TEXT = """
💡 <b>راهنمای کار با ربات دنگ‌بگیر (Dong Calculator)</b>

این ربات به شما و دوستانتان کمک می‌کند هزینه‌های مشترک (سفر، هم‌خانه‌ای، کافه، پروژه‌ها و...) را به‌صورت کاملاً دقیق و خودکار مدیریت کنید:

<b>۱. ساخت گروه و دعوت دوستان:</b>
با زدن دکمه <b>«ایجاد گروه دنگ جدید»</b> یک گروه بسازید. سپس از منوی گروه گزینه <b>«لینک دعوت به گروه»</b> را بزنید و لینک را برای دوستانتان بفرستید تا با یک کلیک عضو شوند.

<b>۲. ثبت هزینه:</b>
هر زمان کسی خریدی انجام داد، دکمه <b>«💸 ثبت هزینه جدید»</b> را بزنید:
• عنوان هزینه را بنویسید (مثلاً: بنزین یا ناهار رستوران)
• مبلغ را وارد کنید (به تومان، مثلاً ۴۵۰۰۰۰ یا 450,000)
• شخص پرداخت‌کننده را مشخص کنید
• افراد سهیم در دنگ را تعیین کنید (تقسیم مساوی بین همه یا انتخاب افراد خاص)

<b>۳. گزارش و فرمول تسویه:</b>
• <b>گزارش حساب‌ها:</b> جمع کل خرج‌ها، سهم هر نفر و طلبکاری/بدهکاری را شفاف نشان می‌دهد.
• <b>فرمول تسویه حساب:</b> با هوشمندی کامل مشخص می‌کند دقیقاً <i>چه کسی باید چقدر به چه کسی پرداخت کند</i> تا با <u>کمترین تعداد تراکنش</u> حساب‌ها صاف شوند!

<b>۴. صفر کردن حساب‌ها:</b>
وقتی بچه‌ها با هم حساب کتاب را انجام دادند، با زدن <b>«🔄 صفر کردن حساب‌ها»</b> دوره مالی بسته شده و حساب‌ها برای خریدهای بعدی صفر می‌شوند (بدون پاک شدن تاریخچه).
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
        f"سلام <b>{user.full_name}</b> عزیز! خوش آمدید 🌺\n\n"
        "به ربات محاسبه دنگ و مدیریت هزینه‌های مشترک خوش آمدید.\n"
        "برای شروع می‌توانید یک گروه جدید بسازید یا وارد گروه‌های قبلی خود شوید:"
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
