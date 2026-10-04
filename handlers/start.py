from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from helpers import safe

router = Router()

HELP_TEXT = """
☕ <b>راهنمای کافه دنگ؛ رفیق روزهای خرج و دورهمی!</b>

کار با من خیلی ساده‌ست داداش! این چند تا نکته رو بدون تا حساب‌کتاب‌هاتون مثل آب خوردن حل شه:

<b>۱. اول کارت‌های بانکیت رو ثبت کن:</b>
برو تو بخش <b>«💳 شماره کارت بانکی من»</b> و هر چند تا کارتی که داری ثبت کن. کارت اصلیت رو هم ستاره‌دار کن تا وقتی از کسی طلبکار شدی، شماره کارتت مستقیم بیفته جلو چشمش و بهونه‌ای برای ندادن دنگ نمونه! 😉

<b>۲. گروه بساز و بچه‌ها رو بیار تو کافه:</b>
با دکمه <b>«➕ ایجاد گروه دنگ جدید»</b> یه اسم باحال (یا رندوم خنده‌دار) بذار، بعد <b>«💌 کارت دعوت اعضا»</b> رو برای دوستانت بفرست تا با لقب‌های جالب و رندوم وارد جمع بشن.

<b>۳. لحن گپ من رو تنظیم کن:</b>
تو تنظیمات هر گروه می‌تونی بگی چطوری باهاتون حرف بزنم:
• 👔 <b>رسمی:</b> شیک و اداری برای همکارها و پروژه‌ها
• 😊 <b>دوستانه:</b> صمیمی و رفاقتی برای جمع رفقا
• 🔞 <b>بی‌ادب (+18):</b> شوخی‌های تند، تیکه‌انداز و دنگ‌گیری زوری!

<b>۴. خرج‌هاتون رو ثبت کنید:</b>
هر کی هر جا پیاده شد، دکمه <b>«💸 ثبت هزینه جدید»</b> رو می‌زنه. می‌تونی هزینه رو مساوی بین همه یا فقط بین کسایی که بودن تقسیم کنی.

<b>۵. تسویه حساب و یادآوری:</b>
تو بخش <b>«⚖️ فرمول تسویه حساب»</b> من با ریاضی هوشمند طوری حساب می‌کنم که با کمترین تعداد کارت‌به‌کارت همه چی صاف شه. حتی دکمه اعلام واریز و یادآوری به بدحساب‌ها هم داریم!

<b>۶. صفر کردن حساب‌ها:</b>
وقتی همه با هم صاف کردن، دکمه <b>«🔄 صفر کردن حساب‌ها»</b> رو بزنید تا دوره بسته شه و برای سفر یا دورهمی بعدی آماده شیم! 🌸
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
                    f"🎉 <b>به به! خوش اومدی به دورهمی «{safe(group['title'])}»</b> ☕✨\n\n"
                    f"👑 بچه‌ها برات لقب باحال <b>«{safe(nickname)}»</b> رو گذاشتن! 😅\n\n"
                    f"👥 جمعمون تا الان {len(members)} نفره شده. بریم تو داشبورد گروه ببینیم چه خبره:"
                )
            else:
                msg = (
                    f"سلام دوباره رفیق! تو که قبلاً با لقب <b>«{safe(nickname)}»</b> تو جمع <b>«{safe(group['title'])}»</b> بودی! 😉\n\n"
                    f"👥 جمعمون {len(members)} نفره‌ست. بریم سراغ حساب‌کتاب‌ها:"
                )
            
            await message.answer(
                msg,
                parse_mode="HTML",
                reply_markup=kb.group_dashboard_keyboard(group["id"])
            )
            return
        else:
            await message.answer("⚠️ این لینک دعوت کار نمی‌کنه رفیق! یا منقضی شده یا اشتباه فرستادی.")

    welcome_text = (
        f"به به! سلام <b>{safe(user.full_name)}</b> جان، صفا آوردی رفیق! ☕🥐\n\n"
        "دمت گرم که اومدی <b>کافه دنگ</b>. از این به بعد دیگه غصه حساب‌کتاب و دنگ‌گیری دورهمی‌ها، سفرها و کافه‌گردی‌هاتو نخور؛ همه‌ش با من!\n\n"
        "خیالت راحت، من حواسم به تک‌تک ریال‌های خرج‌شده هست تا آخر هر برنامه، بدون کوچک‌ترین دلخوری و با کمترین کارت‌به‌کارت ممکن حساب همه‌مون صاف شه 🤝\n\n"
        "🎭 <b>یه ویژگی باحال:</b> می‌تونی مشخص کنی چطوری باهاتون صحبت کنم؛ اگه جمع اداریه رسمی باشم، یا همین‌طور رفاقتی و خودمونی گپ بزنیم، یا حتی تو جمع‌های پایه بزنیم رو حالت +18 تا حسابی کل‌کل کنیم! 😈\n\n"
        "خب رفیق، از کجا شروع کنیم؟ دکمه مورد نظرت رو بزن تا بریم جلو:"
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


@router.message(Command("cancel"))
@router.message(F.text.in_(["لغو", "انصراف", "کنسل", "cancel", "Cancel"]))
async def handle_cancel(message: Message, state: FSMContext):
    """لغو عملیات جاری و پاکسازی حالت FSM"""
    current_state = await state.get_state()
    await state.clear()
    if current_state:
        await message.answer("❌ عملیات جاری لغو شد و به منوی اصلی برگشتید.", reply_markup=kb.main_menu_keyboard())
    else:
        await message.answer("ℹ️ در حال حاضر عملیات فعالی وجود ندارد.", reply_markup=kb.main_menu_keyboard())


@router.callback_query(F.data == "nav:main")
async def handle_nav_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    user = callback.from_user
    welcome_text = (
        f"جانم <b>{safe(user.full_name)}</b> جان! در خدمتم رفیق ☕\n\n"
        "چه کاری برات انجام بدم؟ از منوی زیر انتخاب کن تا بریم جلو:"
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

