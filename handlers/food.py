import random
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
from states import FoodPickerStates
from tones import msg_food_picker_intro, msg_food_winner

router = Router()

@router.callback_query(F.data.startswith("food:start:"))
async def handle_food_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    if not group:
        await callback.answer("گروه یافت نشد!", show_alert=True)
        return

    group_tone = await db.get_group_tone(group_id)
    await state.clear()
    await state.update_data(group_id=group_id, items=[], tone=group_tone, group_title=group["title"])
    await state.set_state(FoodPickerStates.waiting_for_items)

    text = msg_food_picker_intro(group_tone, group["title"], [])
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.food_picker_keyboard(group_id, 0)
    )


@router.message(FoodPickerStates.waiting_for_items)
async def handle_food_item_input(message: Message, state: FSMContext):
    raw_text = (message.text or "").strip()
    if not raw_text:
        return

    data = await state.get_data()
    group_id = data.get("group_id")
    group_title = data.get("group_title") or "گروه"
    group_tone = data.get("tone") or "friendly"
    current_items: list[str] = list(data.get("items", []))

    # پشتیبانی از ورود تکی یا چندتایی با کاما یا خط جدید
    new_candidates = []
    normalized = raw_text.replace("،", "\n").replace(",", "\n")
    for line in normalized.split("\n"):
        item = line.strip()
        if item and len(item) <= 60 and item not in current_items and item not in new_candidates:
            new_candidates.append(item)

    if not new_candidates:
        await message.answer("⚠️ لطفاً نام غذای معتبر وارد کنید (گزینه‌های تکراری اضافه نمی‌شوند):")
        return

    current_items.extend(new_candidates)
    await state.update_data(items=current_items)

    text = msg_food_picker_intro(group_tone, group_title, current_items)
    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=kb.food_picker_keyboard(group_id, len(current_items))
    )


@router.callback_query(F.data.startswith("food:spin:"))
async def handle_food_spin(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    group_title = group["title"] if group else data.get("group_title", "گروه")
    group_tone = (await db.get_group_tone(group_id)) if group else data.get("tone", "friendly")
    
    items = data.get("items", [])
    if len(items) < 2:
        await callback.answer("⚠️ برای قرعه‌کشی حداقل باید ۲ گزینه غذا وارد کنید!", show_alert=True)
        return

    await callback.answer("🎲 گردونه چرخید...")
    winner = random.choice(items)

    text = msg_food_winner(group_tone, group_title, winner, len(items))
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.food_result_keyboard(group_id)
    )


@router.callback_query(F.data.startswith("food:clear:"))
async def handle_food_clear(callback: CallbackQuery, state: FSMContext):
    await callback.answer("🔄 لیست غذاها پاک شد.")
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    group_title = group["title"] if group else "گروه"
    group_tone = await db.get_group_tone(group_id)

    await state.update_data(items=[])
    await state.set_state(FoodPickerStates.waiting_for_items)

    text = msg_food_picker_intro(group_tone, group_title, [])
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.food_picker_keyboard(group_id, 0)
    )


@router.callback_query(F.data.startswith("food:add_more:"))
async def handle_food_add_more(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    group = await db.get_group_by_id(group_id)
    group_title = group["title"] if group else "گروه"
    group_tone = await db.get_group_tone(group_id)

    data = await state.get_data()
    items = data.get("items", [])
    await state.set_state(FoodPickerStates.waiting_for_items)

    text = msg_food_picker_intro(group_tone, group_title, items)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=kb.food_picker_keyboard(group_id, len(items))
    )
