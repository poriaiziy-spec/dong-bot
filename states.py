from aiogram.fsm.state import State, StatesGroup

class GroupCreationStates(StatesGroup):
    waiting_for_title = State()

class ExpenseCreationStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_amount = State()
    waiting_for_unit_price = State()
    waiting_for_quantity = State()
    waiting_for_payer = State()
    waiting_for_shares = State()

class CardRegistrationStates(StatesGroup):
    waiting_for_card_number = State()
    waiting_for_bank_name = State()

class FoodPickerStates(StatesGroup):
    waiting_for_items = State()

class NamePromptStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_confirm = State()

class ExpenseEditStates(StatesGroup):
    waiting_for_new_amount = State()

class ShoppingItemStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_unit_price = State()
    waiting_for_quantity = State()
    waiting_for_item_price_batch = State()
    waiting_for_lump_sum = State()
    waiting_for_edit_input = State()

