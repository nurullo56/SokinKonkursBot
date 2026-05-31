import logging

from aiogram import Router
from aiogram.types import ChatJoinRequest

from database.connection import Database

logger = logging.getLogger(__name__)
router = Router()


@router.chat_join_request()
async def record_zayafka_request(request: ChatJoinRequest, db: Database) -> None:
    logger.info("JOIN REQUEST received: user=%s chat=%s", request.from_user.id, request.chat.id)
    zayafka_rows = await db.fetchall("SELECT channel_id FROM zayafka_channels")
    zayafka_ids = {str(row["channel_id"]).strip() for row in zayafka_rows}
    logger.info("Zayafka IDs in DB: %s", zayafka_ids)

    if str(request.chat.id) not in zayafka_ids:
        return

    await db.execute(
        "INSERT OR IGNORE INTO zayafka_join_requests (user_id, channel_id) VALUES (?, ?)",
        (request.from_user.id, str(request.chat.id)),
    )
    await db.commit()
    logger.info(
        "Recorded zayafka join request: user=%s channel=%s",
        request.from_user.id,
        request.chat.id,
    )
