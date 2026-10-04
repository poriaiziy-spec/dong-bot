from aiogram.fsm.state import State, StatesGroup

class GroupCreationStates(StatesGroup):
    waiting_for_title = State()

class ExpenseCreationStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_amount = State()
    waiting_for_payer = State()
    waiting_for_shares = State()
