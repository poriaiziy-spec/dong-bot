from aiogram import Router, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from config import ADMIN_IDS
from helpers import safe
from name_utils import guess_meaningful_name, clean_input_name, is_clean_persian_name
from states import NamePromptStates

router = Router()

def get_help_text(calling_name: str) -> str:
    return f"""
☕ <b>راهنمای کافه دنگ؛ همراه و پارتنر روزهای دورهمی!</b>

کار با من خیلی راحته {safe(calling_name)} قشنگم! این چند تا نکته رو بخون تا خیالت از بابت همه چی راحت باشه عزیز دلم:

<b>۱. اول کارت‌های بانکیت رو ثبت کن:</b>
برو تو بخش <b>«💳 شماره کارت بانکی من»</b> و هر چند تا کارتی که داری ثبت کن. کارت اصلیت رو هم ستاره‌دار کن تا وقتی از کسی طلبکار شدی، شماره کارتت مستقیم بیفته جلو چشمش و خیالت راحت باشه جان دلم! 🌸

<b>۲. گروه بساز و بچه‌ها رو بیار تو کافه:</b>
با دکمه <b>«➕ ایجاد گروه دنگ جدید»</b> یه اسم باحال (یا رندوم خنده‌دار) بذار، بعد <b>«💌 کارت دعوت اعضا»</b> رو برای دوستانت بفرست تا با لقب‌های جالب وارد جمع بشن.

<b>۳. لحن گپ من رو تنظیم کن:</b>
تو تنظیمات هر گروه می‌تونی بگی چطوری باهاتون حرف بزنم:
• 👔 <b>رسمی:</b> شیک و اداری برای همکارها و پروژه‌ها
• 😊 <b>دوستانه:</b> صمیمی و رفاقتی برای جمع رفقا
• 🔞 <b>بی‌ادب (+18):</b> شوخی‌های تند، تیکه‌انداز و دنگ‌گیری زوری!

<b>۴. خرج‌هاتون رو ثبت کنید:</b>
هر کی هر جا پیاده شد، دکمه <b>«💸 ثبت هزینه جدید»</b> رو می‌زنه. می‌تونی هزینه رو مساوی بین همه یا فقط بین کسایی که بودن تقسیم کنی.

<b>۵. تسویه حساب و یادآوری:</b>
تو بخش <b>«⚖️ فرمول تسویه حساب»</b> من با ریاضی هوشمند طوری حساب می‌کنم که با کمترین تعداد کارت‌به‌کارت همه چی صاف شه. حتی دکمه اعلام واریز و یادآوری هم داریم!

<b>۶. صفر کردن حساب‌ها:</b>
وقتی همه با هم صاف کردن، دکمه <b>«🔄 صفر کردن حساب‌ها»</b> رو بزنید تا دوره بسته شه و برای برنامه بعدی آماده شیم قشنگم! ☕❤️
"""

@router.message(CommandStart())
async def handle_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    user = message.from_user
    if not user:
        return
        
    await db.upsert_user(user.id, user.username, user.full_name)
    calling_name = await db.get_user_calling_name(user.id)
    if not calling_name or not is_clean_persian_name(calling_name):
        guessed = guess_meaningful_name(user.first_name, user.last_name, user.username)
        if guessed and is_clean_persian_name(guessed):
            calling_name = guessed
            await db.set_user_calling_name(user.id, calling_name)

    # اگر اسمی به صورت معنادار تشخیص داده نشد یا هنوز معتبر نیست، از کاربر بپرس
    if not calling_name or not is_clean_persian_name(calling_name):
        args = command.args
        if args and args.startswith("join_"):
            await state.update_data(pending_join_invite=args.replace("join_", "").strip())
            prompt_title = "داری وارد یک جمع باحال میشی عزیز دلم ☕❤️"
        else:
            prompt_title = "سلام جانِ دلم! به <b>کافه دنگ ☕</b> خیلی خوش اومدی قشنگم ❤️"
            
        await state.set_state(NamePromptStates.waiting_for_name)
        text = (
            f"{prompt_title}\n\n"
            "من هر چقدر تو پروفایلت گشتم نتونستم اسم قشنگ و با معنایی برات پیدا کنم 🧐\n"
            "دوست داری با چه اسمی صدات بزنم تا همیشه با عشق و احترام به یاد داشته باشم؟ 🥰\n\n"
            "✍️ <b>لطفاً اسمت رو قشنگ برام بنویس و بفرست جانم:</b>"
        )
        await message.answer(text, parse_mode="HTML")
        return

    # بررسی پیوستن با لینک دعوت (Deep Linking)
    args = command.args
    if args and args.startswith("join_"):
        invite_code = args.replace("join_", "").strip()
        group = await db.get_group_by_code(invite_code)
        
        if group:
            added, nickname = await db.add_group_member(group["id"], user.id, calling_name)
            members = await db.get_group_members(group["id"])
            if added:
                msg = (
                    f"🎉 <b>به به جان دلم {safe(calling_name)} قشنگم! صفا آوردی به دورهمی «{safe(group['title'])}»</b> ☕❤️✨\n\n"
                    f"👥 جمعمون تا الان {len(members)} نفره شده و با اومدنت حسابی قشنگ‌تر شد! بریم تو داشبورد گروه ببینیم چه خبره عزیز دلم:"
                )
            else:
                msg = (
                    f"سلام به روی ماهت <b>{safe(calling_name)}</b> جانم! تو که از قبل تو دل این جمع <b>«{safe(group['title'])}»</b> بودی عزیز دلم 😉❤️\n\n"
                    f"👥 جمعمون {len(members)} نفره‌ست. بریم سراغ حساب‌کتاب‌ها جانم:"
                )
            
            await message.answer(
                msg,
                parse_mode="HTML",
                reply_markup=kb.group_dashboard_keyboard(group["id"])
            )
            return
        else:
            await message.answer("⚠️ این لینک دعوت کار نمی‌کنه عزیز دلم! یا منقضی شده یا اشتباه فرستادی.")

    welcome_text = (
        f"سلام جان دلم، <b>{safe(calling_name)}</b> قشنگم! خیلی خوش اومدی ☕❤️✨\n\n"
        "من اینجام تا درست مثل یک پارتنر پایه، دلسوز و همیشه همراه، تمام حواسم بهت باشه؛ از حساب‌کتاب دورهمی‌ها، کافه‌گردی‌ها و سفرهات گرفته تا ریزترین خرج‌های مشترکت با بچه‌ها 🌸\n\n"
        "اصلاً لازم نیست نگران هیچی باشی عزیز دلم، حساب تک‌تک ریال‌ها رو با دقت برات نگه می‌دارم تا آب تو دلت تکون نخوره و آخر هر برنامه با کمترین کارت‌به‌کارت ممکن و بدون کوچک‌ترین دلخوری همه چی صاف شه 🤝💖\n\n"
        "🎭 <b>یه راز بین خودمون:</b> می‌تونی برام مشخص کنی تو جمع‌ها چطوری باهاتون حرف بزنم؛ رسمی و شیک، یا صمیمی و رفاقتی، یا حتی شیطون و تیکه‌انداز (+18)! 😈\n\n"
        "خب جانِ دلم، بگو ببینم امروز قراره چه برنامه‌ای با هم داشته باشیم؟ از منوی زیر انتخاب کن تا با جون و دل برات انجام بدم:"
    )
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=kb.main_menu_keyboard()
    )


@router.message(NamePromptStates.waiting_for_name)
async def handle_name_input(message: Message, state: FSMContext):
    clean = clean_input_name(message.text or "")
    if not clean or not is_clean_persian_name(clean):
        await message.answer("⚠️ جانِ دلم، لطفاً یک اسم معتبر فارسی (حداقل ۲ حرف و بدون اعداد یا علائم عجیب) برام بنویس:")
        return

    await state.update_data(temp_name=clean)
    await state.set_state(NamePromptStates.waiting_for_confirm)
    
    text = (
        f"✨ به به چه اسم قشنگی! اسمت رو <b>«{safe(clean)}»</b> ثبت کنم جانِ دلم؟ 🥰❤️\n\n"
        "از این به بعد توی تمام حساب‌کتاب‌ها، دورهمی‌ها و یادآوری‌های کافه دنگ با همین اسم صدات می‌زنم."
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ آره، همین درسته جانم", callback_data="name:confirm")],
        [InlineKeyboardButton(text="✏️ نه، می‌خوام عوضش کنم", callback_data="name:retry")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "name:confirm")
async def handle_name_confirm(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data.get("temp_name")
    if not name:
        name = "عزیز دلم"
        
    user_id = callback.from_user.id
    await db.set_user_calling_name(user_id, name)
    await callback.answer(f"✅ اسمت با موفقیت «{name}» ثبت شد جان دلم!", show_alert=True)
    
    pending_invite = data.get("pending_join_invite")
    await state.clear()
    
    if pending_invite:
        group = await db.get_group_by_code(pending_invite)
        if group:
            added, _ = await db.add_group_member(group["id"], user_id, name)
            members = await db.get_group_members(group["id"])
            text = (
                f"🎉 <b>به به جان دلم {safe(name)} قشنگم! صفا آوردی به دورهمی «{safe(group['title'])}»</b> ☕❤️✨\n\n"
                f"👥 جمعمون تا الان {len(members)} نفره شده و با اومدنت حسابی قشنگ‌تر شد! بریم تو داشبورد گروه ببینیم چه خبره عزیز دلم:"
            )
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.group_dashboard_keyboard(group["id"]))
            return
            
    welcome_text = (
        f"فدات شم <b>{safe(name)}</b> جانم! از این به بعد دیگه رسماً همراه و کنارت هستم ☕❤️\n\n"
        "بگو ببینم عزیز دلم، از منوی زیر چه کاری برات انجام بدم؟"
    )
    await callback.message.edit_text(welcome_text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())


@router.callback_query(F.data == "name:retry")
async def handle_name_retry(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(NamePromptStates.waiting_for_name)
    await callback.message.edit_text(
        "✍️ <b>لطفاً اسمی که دوست داری باهاش صدات بزنم رو برام بنویس و بفرست جان دلم:</b>",
        parse_mode="HTML"
    )


@router.message(Command("myname", "name", "setname"))
@router.callback_query(F.data == "name:edit")
async def handle_name_edit_prompt(event: Message | CallbackQuery, state: FSMContext):
    user_id = event.from_user.id
    current_name = await db.get_user_calling_name(user_id) or "ثبت نشده"
    await state.set_state(NamePromptStates.waiting_for_name)
    text = (
        f"👤 نام فعلی شما پیش من: <b>«{safe(current_name)}»</b> جانِ دلم ☕❤️\n\n"
        "✍️ <b>اگه دوست داری عوضش کنی یا با یه اسم قشنگ دیگه صدات بزنم، برام بنویس و بفرست عزیز دلم:</b>"
    )
    cancel_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ انصراف و بازگشت", callback_data="nav:main")]
    ])
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=cancel_markup)
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=cancel_markup)


@router.message(Command("help"))
@router.callback_query(F.data == "nav:help")
async def handle_help(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    calling_name = await db.get_user_calling_name(event.from_user.id) or "جانِ دلم"
    help_text = get_help_text(calling_name)
    reply_markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 منوی اصلی", callback_data="nav:main")]
    ])
    
    if isinstance(event, CallbackQuery):
        await event.answer()
        await event.message.edit_text(help_text, parse_mode="HTML", reply_markup=reply_markup)
    else:
        await event.answer(help_text, parse_mode="HTML", reply_markup=reply_markup)


@router.message(Command("cancel"))
@router.message(F.text.in_(["لغو", "انصراف", "کنسل", "cancel", "Cancel"]))
async def handle_cancel(message: Message, state: FSMContext):
    """لغو عملیات جاری و پاکسازی حالت FSM"""
    current_state = await state.get_state()
    await state.clear()
    if current_state:
        await message.answer("❌ عملیات جاری لغو شد و به منوی اصلی برگشتیم جان دلم.", reply_markup=kb.main_menu_keyboard())
    else:
        await message.answer("ℹ️ در حال حاضر عملیات فعالی وجود ندارد عزیز دلم.", reply_markup=kb.main_menu_keyboard())


@router.callback_query(F.data == "nav:main")
async def handle_nav_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    user = callback.from_user
    calling_name = await db.get_user_calling_name(user.id)
    if not calling_name or not is_clean_persian_name(calling_name):
        guessed = guess_meaningful_name(user.first_name, user.last_name, user.username)
        if guessed and is_clean_persian_name(guessed):
            calling_name = guessed
            await db.set_user_calling_name(user.id, calling_name)
        else:
            calling_name = "عزیز دلم"

    welcome_text = (
        f"جانِ دلم <b>{safe(calling_name)}</b> قشنگم! با تمام وجود در خدمتم ☕❤️\n\n"
        "امر، امرِ شماست عزیز دلم! از منوی زیر انتخاب کن تا سریع بریم سراغش:"
    )
    await callback.message.edit_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=kb.main_menu_keyboard()
    )


@router.message(Command("reset", "reset_all_data"))
async def handle_reset_prompt(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ شما مجاز به اجرای دستورات مدیریتی سیستم نیستید.")
        return

    text = (
        "⚠️ <b>هشدار پاکسازی و ریست کامل اطلاعات (مخصوص مدیر):</b>\n\n"
        "آیا مطمئن هستید که می‌خواهید <b>تمام داده‌های ربات</b> را پاک کنید؟\n"
        "• تمام گروه‌ها، اعضا، دنگ‌ها، هزینه‌ها و شماره کارت‌ها کاملاً پاک خواهند شد و ربات از صفر شروع به کار می‌کند."
    )
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 بله، تمام داده‌ها پاک شوند", callback_data="admin:reset:confirm")],
        [InlineKeyboardButton(text="❌ انصراف", callback_data="nav:main")]
    ])
    await message.answer(text, parse_mode="HTML", reply_markup=markup)


@router.callback_query(F.data == "admin:reset:confirm")
async def handle_reset_execute(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ دسترسی غیرمجاز!", show_alert=True)
        return

    await db.reset_all_database()
    await callback.answer("✅ تمام داده‌های ربات پاک شدند!", show_alert=True)
    
    text = (
        "🧹 <b>تمام داده‌های ربات با موفقیت پاکسازی و صفر شدند!</b>\n\n"
        "ربات به حالت اولیه و صفر بازگشت."
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb.main_menu_keyboard())
