import json
import logging
import re
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, or_f
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from database.connection import Database
from keyboards.admin_kb import BTN_CANCEL, BTN_RESULTS, get_admin_reply_keyboard, get_cancel_keyboard
from services.verification_service import VerificationService
from states.admin import ResultsFlow

logger = logging.getLogger(__name__)
router = Router()

_PLACE_EMOJIS = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]

BTN_CONFIRM_SEND = "✅ Ha, kanalga yuborish"
BTN_SKIP_LINK    = "➡️ Havola siz, oddiy yuborish"
BTN_4_WINNERS    = "4️⃣ 4 ta g'olib"
BTN_5_WINNERS    = "5️⃣ 5 ta g'olib"


def get_count_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_4_WINNERS), KeyboardButton(text=BTN_5_WINNERS)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def get_confirm_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_CONFIRM_SEND)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def get_link_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SKIP_LINK)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def _parse_message_link(link: str) -> tuple[str | int | None, int | None]:
    m = re.match(r"https?://t\.me/c/(\d+)/(\d+)", link)
    if m:
        return int("-100" + m.group(1)), int(m.group(2))
    m = re.match(r"https?://t\.me/(\w+)/(\d+)", link)
    if m:
        return "@" + m.group(1), int(m.group(2))
    return None, None


@router.message(or_f(Command("results"), F.text == BTN_RESULTS))
async def cmd_results(message: Message, state: FSMContext, db: Database) -> None:
    channel_id_str = await db.get_setting("channel_id")
    if not channel_id_str:
        await message.answer("❌ Kanal ID belgilanmagan.")
        return
    try:
        int(channel_id_str)
    except ValueError:
        await message.answer("❌ Kanal ID noto'g'ri formatda.")
        return

    await state.set_state(ResultsFlow.waiting_count)
    await message.answer(
        "🏆 <b>Natijalar</b>\n\nNechta g'olib tanlansin?",
        reply_markup=get_count_keyboard(),
    )


@router.message(ResultsFlow.waiting_count)
async def results_get_count(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_reply_keyboard())
        return

    if message.text == BTN_4_WINNERS:
        count = 4
    elif message.text == BTN_5_WINNERS:
        count = 5
    else:
        await message.answer("Iltimos tugmalardan birini tanlang:", reply_markup=get_count_keyboard())
        return

    channel_id_str = await db.get_setting("channel_id")
    channel_id = int(channel_id_str)

    await message.answer(f"⏳ {count} ta g'olib tanlanmoqda...")

    verified_users = await db.fetchall(
        "SELECT user_id, contest_number, first_name, username, referral_count "
        "FROM users WHERE verified = TRUE "
        "ORDER BY referral_count DESC"
    )
    if len(verified_users) < count:
        await state.clear()
        await message.answer(
            f"❌ Tasdiqlangan ishtirokchilar kamida {count} ta bo'lishi kerak. "
            f"Hozirda: {len(verified_users)} ta",
            reply_markup=get_admin_reply_keyboard(),
        )
        return

    verification_svc = VerificationService(db, bot)
    winners: list[dict] = []
    skipped = 0
    for user in verified_users:
        if len(winners) >= count:
            break
        if await verification_svc.check_user_in_bot(user["user_id"]):
            winners.append(user)
        else:
            skipped += 1

    if len(winners) < count:
        await state.clear()
        await message.answer(
            f"❌ Yetarli faol ishtirokchi yo'q.\n"
            f"Faol: {len(winners)}, bloklagan/ketgan: {skipped}",
            reply_markup=get_admin_reply_keyboard(),
        )
        return

    lines = ["🏆 KONKURS NATIJALARI\n"]
    for i, winner in enumerate(winners):
        full_name = (winner.get("first_name") or "").strip() or winner.get("username") or str(winner["user_id"])
        lines.append(f"{_PLACE_EMOJIS[i]} {i + 1}-o'rin — {escape(full_name)} — {winner['referral_count']} ta referal — Raqam: {winner['contest_number']}")
    lines.append("\nTabriklaymiz! 🎉")
    result_text = "\n".join(lines)

    await state.set_state(ResultsFlow.waiting_reply_link)
    await state.update_data(
        winners=json.dumps(winners),
        result_text=result_text,
        channel_id=channel_id,
    )

    await message.answer(
        f"👀 <b>G'oliblar ko'rinishi:</b>\n\n{result_text}\n\n"
        f"🔗 Qaysi kanal xabariga reply qilinsin?\n"
        f"Xabar havolasini yuboring yoki o'tkazib yuboring:",
        reply_markup=get_link_keyboard(),
    )


@router.message(ResultsFlow.waiting_reply_link)
async def results_get_link(message: Message, state: FSMContext) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=get_admin_reply_keyboard())
        return

    reply_chat = None
    reply_msg_id = None

    if message.text and message.text != BTN_SKIP_LINK:
        reply_chat, reply_msg_id = _parse_message_link(message.text.strip())
        if reply_chat is None:
            await message.answer("❌ Havola noto'g'ri. Qaytadan yuboring yoki o'tkazib yuboring:")
            return

    await state.update_data(reply_chat=str(reply_chat) if reply_chat else None, reply_msg_id=reply_msg_id)
    await state.set_state(ResultsFlow.confirm)
    await message.answer(
        "⚠️ Kanalga yuborilsinmi?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text=BTN_CONFIRM_SEND)], [KeyboardButton(text=BTN_CANCEL)]],
            resize_keyboard=True,
        ),
    )


@router.message(ResultsFlow.confirm, F.text == BTN_CONFIRM_SEND)
async def confirm_results(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    data = await state.get_data()
    winners: list[dict] = json.loads(data["winners"])
    result_text: str = data["result_text"]
    channel_id: int = data["channel_id"]
    reply_chat = data.get("reply_chat")
    reply_msg_id = data.get("reply_msg_id")
    await state.clear()

    for place, winner in enumerate(winners, 1):
        try:
            await db.execute(
                "INSERT INTO winners (user_id, place, contest_number) VALUES (?, ?, ?)",
                (winner["user_id"], place, winner["contest_number"]),
            )
        except Exception as exc:
            logger.error("Failed to save winner %s: %s", winner["user_id"], exc)
    await db.commit()

    try:
        if reply_chat and reply_msg_id:
            chat = int(reply_chat) if reply_chat.lstrip("-").isdigit() else reply_chat
            await bot.send_message(chat, result_text, reply_to_message_id=reply_msg_id)
        else:
            await bot.send_message(channel_id, result_text)
        await message.answer("✅ Natijalar kanalga yuborildi!", reply_markup=get_admin_reply_keyboard())
    except Exception as exc:
        logger.error("Failed to post results: %s", exc)
        await message.answer(
            f"❌ Kanalga yuborishda xato: {exc}\n\nNatijalar:\n\n{result_text}",
            reply_markup=get_admin_reply_keyboard(),
        )


@router.message(ResultsFlow.confirm, F.text == BTN_CANCEL)
async def cancel_results(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Natijalar yuborilmadi.", reply_markup=get_admin_reply_keyboard())
