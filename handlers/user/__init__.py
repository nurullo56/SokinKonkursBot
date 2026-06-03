from aiogram import F, Router
from aiogram.enums import ChatType

from handlers.user.group_handlers import router as group_router
from handlers.user.join_request import router as join_request_router
from handlers.user.start import router as start_router
from handlers.user.statistics import router as stats_router
from middlewares.anti_flood import AntiFloodMiddleware
from middlewares.queue_middleware import QueueMiddleware
from middlewares.subscription_middleware import SubscriptionMiddleware

# Faqat private chat handlerlari
user_router = Router()
user_router.message.filter(F.chat.type == ChatType.PRIVATE)
user_router.message.middleware(QueueMiddleware(max_concurrent=20))
user_router.callback_query.middleware(QueueMiddleware(max_concurrent=20))
user_router.message.middleware(AntiFloodMiddleware(limit=3, window=5.0))
user_router.message.middleware(SubscriptionMiddleware())
user_router.callback_query.middleware(SubscriptionMiddleware())

user_router.include_router(join_request_router)
user_router.include_router(start_router)
user_router.include_router(stats_router)

__all__ = ["user_router", "group_router"]
