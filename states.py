from aiogram.fsm.state import State, StatesGroup

class GroupCreationStates(StatesGroup):
    waiting_for_title = State()

class ExpenseCreationStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_amount = State()
    waiting_for_payer = State()
    waiting_for_shares = State()

class CardRegistrationStates(StatesGroup):
    waiting_for_card_number = State()
    waiting_for_bank_name = State()

class FoodPickerStates(StatesGroup):
    waiting_for_items = State()

