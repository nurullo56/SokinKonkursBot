from aiogram import F, Router
from aiogram.enums import ChatType

from handlers.admin.channels import router as channels_router
from handlers.admin.panel import router as panel_router
from handlers.admin.results import router as results_router
from handlers.admin.settings import router as settings_router
from handlers.admin.broadcast import router as broadcast_router
from middlewares.admin_middleware import AdminMiddleware
from middlewares.anti_flood import AntiFloodMiddleware

admin_router = Router()

admin_router.message.filter(F.chat.type == ChatType.PRIVATE)
admin_router.message.middleware(AntiFloodMiddleware(limit=5, window=3.0))
admin_router.message.middleware(AdminMiddleware())
admin_router.callback_query.middleware(AdminMiddleware())

admin_router.include_router(panel_router)
admin_router.include_router(settings_router)
admin_router.include_router(results_router)
admin_router.include_router(channels_router)
admin_router.include_router(broadcast_router)

__all__ = ["admin_router"]