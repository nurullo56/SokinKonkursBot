from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

from database.connection import Database
from services.contest_service import ContestService
from utils.emoji import ce

router = Router()


@router.message(Command("id"), F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def cmd_id(message: Message) -> None:
    await message.reply(f"🆔 Guruh ID: <code>{message.chat.id}</code>")


@router.message(F.photo, F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))
async def handle_group_screenshot(message: Message, db: Database) -> None:
    group_id_str = await db.get_setting("group_id")
    if not group_id_str:
        return

    val = group_id_str.strip()
    if val.lstrip("-").isdigit():
        if message.chat.id != int(val):
            return
    else:
        username = val.lstrip("@").lower()
        if (message.chat.username or "").lower() != username:
            return

    bot_mode = await db.get_setting("bot_mode") or "BOT"
    if bot_mode != "BOT":
        return

    contest_svc = ContestService(db)
    if not await contest_svc.is_contest_active():
        return

    if not message.from_user:
        return

    user_id = message.from_user.id

    row = await db.fetchone(
        "SELECT referral_count, verified FROM users WHERE user_id = ?", (user_id,)
    )
    if not row:
        await message.reply(
            "❗ Siz botda ro'yxatdan o'tmagansiz.\n"
            "Botga kiring va /start bosing: @SokinKonkursBot"
        )
        return

    if row["verified"]:
        return

    count: int = row["referral_count"]
    if count < 5:
        await message.reply(
            f"❌ Hali 5 ta do'st chaqirilmagan!\n\n"
            f"{ce('👥')} Siz taklif qilganlar: <b>{count}/5</b>\n"
            f"{ce('⌛')} Yana <b>{5 - count} ta</b> do'st kerak."
        )
        return

    number = await contest_svc.verify_user(user_id)
    if number is None:
        await message.reply("❌ Raqam berishda xato yuz berdi. Admin bilan bog'laning.")
        return

    user = message.from_user
    full_name = " ".join(filter(None, [user.first_name, user.last_name])).strip() or user.username or str(user.id)
    await message.reply(
        f"{ce('✅')} {full_name}, Sizning xabaringiz qabul qilindi. "
        f"Tartib raqamingiz: <b>{number}</b>"
    )
