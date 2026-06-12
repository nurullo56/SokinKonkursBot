import asyncio
import logging
from aiogram import F, Router
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError

from database.connection import Database
from keyboards.admin_kb import (
    BTN_BROADCAST,
    BTN_CANCEL,
    get_admin_reply_keyboard,
    get_cancel_keyboard,
)
from states.admin import BroadcastFlow

logger = logging.getLogger(__name__)
router = Router()

BTN_CONFIRM = "✅ Tasdiqlash"

def get_confirm_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CONFIRM)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )

@router.message(or_f(F.text == BTN_BROADCAST, Command("broadcast")), StateFilter(None))
async def cmd_broadcast(message: Message, state: FSMContext) -> None:
    await state.set_state(BroadcastFlow.waiting_message)
    await message.answer(
        "📢 <b>Reklama tarqatish bo'limi</b>\n\n"
        "Iltimos, foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.\n"
        "Xabar matn, rasm, video yoki istalgan media ko'rinishida bo'lishi mumkin.",
        reply_markup=get_cancel_keyboard()
    )

@router.message(BroadcastFlow.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_reply_keyboard())
        return

    # Store the message ID and chat ID so we can copy it later
    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id
    )
    
    await state.set_state(BroadcastFlow.confirm_send)
    await message.reply(
        "❓ Ushbu xabarni barcha foydalanuvchilarga yuborishni tasdiqlaysizmi?",
        reply_markup=get_confirm_keyboard()
    )

@router.message(BroadcastFlow.confirm_send)
async def send_broadcast(message: Message, state: FSMContext, db: Database) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_reply_keyboard())
        return

    if message.text != BTN_CONFIRM:
        await message.answer("Iltimos, tasdiqlash uchun tugmalardan foydalaning:")
        return

    data = await state.get_data()
    from_chat_id = data.get("from_chat_id")
    message_id = data.get("message_id")
    
    await state.clear()
    
    if not from_chat_id or not message_id:
        await message.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.", reply_markup=get_admin_reply_keyboard())
        return

    # Botni bloklaganlarni o'tkazib yuboramiz — ularga urinish behuda vaqt.
    users = await db.fetchall("SELECT user_id FROM users WHERE is_blocked = FALSE")
    if not users:
        await message.answer("Foydalanuvchilar topilmadi.", reply_markup=get_admin_reply_keyboard())
        return

    status_message = await message.answer(
        f"⏳ Tarqatish boshlandi...\nJami foydalanuvchilar: {len(users)} ta.",
        reply_markup=get_admin_reply_keyboard()
    )

    success = 0
    failed = 0
    blocked = 0
    blocked_ids: list[int] = []

    for i, user in enumerate(users):
        user_id = user["user_id"]
        try:
            # Copy message to target user
            await message.bot.copy_message(
                chat_id=user_id,
                from_chat_id=from_chat_id,
                message_id=message_id
            )
            success += 1
        except TelegramForbiddenError:
            blocked += 1
            blocked_ids.append(user_id)
        except TelegramAPIError as e:
            logger.error("Failed to send broadcast to %s: %s", user_id, e)
            failed += 1
        except Exception as e:
            logger.error("Unexpected error in broadcast to %s: %s", user_id, e)
            failed += 1

        # Anti-spam delay to respect Telegram limits (30 msg/sec)
        await asyncio.sleep(0.05)

        # Progress update every 100 users
        if (i + 1) % 100 == 0:
            try:
                await status_message.edit_text(
                    f"⏳ Tarqatish jarayoni:\n\n"
                    f"Yuborildi: {i + 1}/{len(users)}\n"
                    f"Muvaffaqiyatli: {success}\n"
                    f"Bloklanganlar: {blocked}\n"
                    f"Xatoliklar: {failed}"
                )
            except Exception:
                pass

    # Bloklaganlarni belgilab qo'yamiz — keyingi broadcast ularni o'tkazib yuboradi.
    if blocked_ids:
        placeholders = ",".join("?" * len(blocked_ids))
        await db.execute(
            f"UPDATE users SET is_blocked = TRUE WHERE user_id IN ({placeholders})",
            tuple(blocked_ids),
        )
        await db.commit()

    await status_message.reply(
        f"✅ <b>Reklama tarqatish yakunlandi!</b>\n\n"
        f"📊 Statistika:\n"
        f"• Jami a'zolar: {len(users)}\n"
        f"• Yetkazildi: {success}\n"
        f"• Bloklaganlar: {blocked}\n"
        f"• Xatoliklar: {failed}"
    )
