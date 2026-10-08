from aiogram import Router
from .start import router as start_router
from .groups import router as groups_router
from .expenses import router as expenses_router
from .reports import router as reports_router
from .card import router as card_router
from .food import router as food_router
from .shopping import router as shopping_router

def setup_routers() -> Router:
    main_router = Router()
    main_router.include_router(start_router)
    main_router.include_router(groups_router)
    main_router.include_router(expenses_router)
    main_router.include_router(reports_router)
    main_router.include_router(card_router)
    main_router.include_router(food_router)
    main_router.include_router(shopping_router)
    return main_router

