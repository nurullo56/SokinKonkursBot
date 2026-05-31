import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.connection import Database
from keyboards.admin_kb import (
    BTN_ADD_PUBLIC,
    BTN_ADD_ZAYAFKA,
    BTN_CANCEL,
    BTN_CHANNELS,
    BTN_DEL_PUBLIC,
    BTN_DEL_ZAYAFKA,
    get_admin_reply_keyboard,
    get_cancel_keyboard,
)
from services.subscription_service import SubscriptionService
from states.admin import AddPublicFlow, AddZayafkaFlow, DelPublicFlow, DelZayafkaFlow

logger = logging.getLogger(__name__)
router = Router()


_ALL_CHANNEL_STATES = StateFilter(
    AddPublicFlow, AddZayafkaFlow, DelPublicFlow, DelZayafkaFlow
)


# ── Universal cancel handler (covers all channel FSM states) ─────────────────

@router.message(F.text == BTN_CANCEL, _ALL_CHANNEL_STATES)
async def fsm_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=get_admin_reply_keyboard())


# ── 📋 Kanallar ro'yxati ─────────────────────────────────────────────────────

@router.message(or_f(Command("channels"), F.text == BTN_CHANNELS))
async def cmd_channels(message: Message, db: Database, bot: Bot) -> None:
    svc = SubscriptionService(db, bot)
    public = await svc.get_public_channels()
    zayafka = await svc.get_zayafka_channels()

    if not public and not zayafka:
        await message.answer(
            "📭 Hech qanday majburiy obuna kanali yo'q.\n\n"
            "➕ Kanal qo'shish yoki 🔐 Zayafka qo'shish tugmalarini bosing."
        )
        return

    lines = ["📋 <b>Majburiy obuna kanallari:</b>\n"]
    if public:
        lines.append(f"📢 Ommaviy ({len(public)} ta):")
        for ch in public:
            name = escape(ch["channel_name"] or ch["channel_id"])
            cid = escape(ch["channel_id"])
            link = ch.get("channel_link") or ""
            limit = ch.get("member_limit", 0) or 0
            joined = ch.get("joined_count", 0) or 0
            limit_str = f" [<b>{joined}/{limit} ta</b>]" if limit > 0 else " [Cheksiz]"
            entry = f'<a href="{link}">{name}</a>' if link else name
            lines.append(f"  • {entry}  <code>{cid}</code>{limit_str}")

    if zayafka:
        if public:
            lines.append("")
        lines.append(f"🔐 Zayafka ({len(zayafka)} ta):")
        for ch in zayafka:
            name = escape(ch["channel_name"] or ch["channel_id"])
            cid = escape(ch["channel_id"])
            link = ch.get("invite_link") or ""
            limit = ch.get("member_limit", 0) or 0
            joined = ch.get("joined_count", 0) or 0
            limit_str = f" [<b>{joined}/{limit} ta</b>]" if limit > 0 else " [Cheksiz]"
            entry = f'<a href="{link}">{name}</a>' if link else name
            lines.append(f"  • {entry}  <code>{cid}</code>{limit_str}")

    lines.append(f"\nJami: {len(public) + len(zayafka)} ta")
    await message.answer("\n".join(lines))


# ── ➕ Ommaviy kanal qo'shish ────────────────────────────────────────────────

@router.message(or_f(Command("addpublic"), F.text == BTN_ADD_PUBLIC))
async def cmd_add_public(message: Message, state: FSMContext) -> None:
    await state.set_state(AddPublicFlow.waiting_channel_id)
    await message.answer(
        "📢 Ommaviy kanal username yoki ID kiriting:\n"
        "Misol: <code>@mening_kanalim</code> yoki <code>-1001234567890</code>",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddPublicFlow.waiting_channel_id)
async def flow_add_public(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    channel_id = message.text.strip()
    if not channel_id.startswith("@") and not channel_id.lstrip("-").isdigit():
        await message.answer("❌ Noto'g'ri format. @ bilan boshlang yoki raqamli ID kiriting:")
        return

    channel_name = channel_id
    channel_link = f"https://t.me/{channel_id.lstrip('@')}"
    try:
        chat = await bot.get_chat(channel_id)
        channel_name = chat.title or channel_id
        if chat.username:
            channel_link = f"https://t.me/{chat.username}"
    except Exception as e:
        logger.warning("Could not fetch channel info %s: %s", channel_id, e)

    await state.update_data(
        channel_id=channel_id,
        channel_name=channel_name,
        channel_link=channel_link
    )
    await state.set_state(AddPublicFlow.waiting_limit)
    await message.answer(
        "📈 Ushbu kanal uchun obunachilar limitini kiriting (masalan: 1000).\n"
        "Ushbu limitga yetganda bot kanalni majburiy obunadan avtomatik ravishda o'chiradi.\n"
        "Limit qo'ymaslik uchun 0 kiriting:",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AddPublicFlow.waiting_limit)
async def flow_add_public_limit(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_reply_keyboard())
        return

    limit_str = message.text.strip()
    if not limit_str.isdigit():
        await message.answer("❌ Iltimos, faqat musbat raqam kiriting (masalan, 500 yoki 0):")
        return

    limit = int(limit_str)
    data = await state.get_data()
    channel_id = data["channel_id"]
    channel_name = data["channel_name"]
    channel_link = data["channel_link"]

    await SubscriptionService(db, bot).add_public_channel(channel_id, channel_name, channel_link, member_limit=limit)
    await state.clear()
    
    limit_info = f"Limit: <b>{limit} ta</b>" if limit > 0 else "Limit: <b>Yo'q (Cheksiz)</b>"
    await message.answer(
        f"✅ Ommaviy kanal qo'shildi:\n"
        f"📢 <b>{escape(channel_name)}</b>  <code>{escape(channel_id)}</code>\n"
        f"⚙️ {limit_info}",
        reply_markup=get_admin_reply_keyboard(),
    )


# ── 🗑 Ommaviy kanal o'chirish ────────────────────────────────────────────────

@router.message(or_f(Command("delpublic"), F.text == BTN_DEL_PUBLIC))
async def cmd_del_public(message: Message, state: FSMContext) -> None:
    await state.set_state(DelPublicFlow.waiting_channel_id)
    await message.answer(
        "🗑 O'chirmoqchi bo'lgan ommaviy kanal ID kiriting:\n"
        "Misol: <code>@kanal</code> yoki <code>-1001234567890</code>",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(DelPublicFlow.waiting_channel_id)
async def flow_del_public(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    channel_id = message.text.strip()
    removed = await SubscriptionService(db, bot).remove_public_channel(channel_id)
    await state.clear()
    if removed:
        await message.answer(
            f"✅ Ommaviy kanal o'chirildi: <code>{escape(channel_id)}</code>",
            reply_markup=get_admin_reply_keyboard(),
        )
    else:
        await message.answer(
            f"❌ Ommaviy kanallar orasida topilmadi: <code>{escape(channel_id)}</code>",
            reply_markup=get_admin_reply_keyboard(),
        )


# ── 🔐 Zayafka kanal qo'shish ────────────────────────────────────────────────

@router.message(or_f(Command("addzayafka"), F.text == BTN_ADD_ZAYAFKA))
async def cmd_add_zayafka(message: Message, state: FSMContext) -> None:
    await state.set_state(AddZayafkaFlow.waiting_channel_id)
    await message.answer(
        "🔐 Zayafka kanal ID kiriting (raqamli):\n"
        "Misol: <code>-1001234567890</code>",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AddZayafkaFlow.waiting_channel_id)
async def flow_zayafka_id(message: Message, state: FSMContext) -> None:
    channel_id = message.text.strip()
    if not channel_id.lstrip("-").isdigit():
        await message.answer("❌ Raqamli ID kiriting (masalan: <code>-1001234567890</code>):")
        return
    await state.update_data(channel_id=channel_id)
    await state.set_state(AddZayafkaFlow.waiting_invite_link)
    await message.answer(
        "🔗 Taklif havolasini kiriting:\n"
        "Misol: <code>https://t.me/+xxxxxxxx</code>"
    )


@router.message(AddZayafkaFlow.waiting_invite_link)
async def flow_zayafka_link(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    invite_link = message.text.strip()
    data = await state.get_data()
    channel_id: str = data["channel_id"]

    channel_name = channel_id
    try:
        chat = await bot.get_chat(int(channel_id))
        channel_name = chat.title or channel_id
    except Exception as e:
        logger.warning("Could not fetch zayafka channel info %s: %s", channel_id, e)

    await state.update_data(
        channel_id=channel_id,
        channel_name=channel_name,
        invite_link=invite_link
    )
    await state.set_state(AddZayafkaFlow.waiting_limit)
    await message.answer(
        "📈 Ushbu zayafka kanali uchun obunachilar limitini kiriting (masalan: 1000).\n"
        "Limitga yetganda bot ushbu kanalni avtomatik ravishda majburiy obunadan o'chiradi.\n"
        "Limit qo'ymaslik uchun 0 kiriting:",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AddZayafkaFlow.waiting_limit)
async def flow_zayafka_limit(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_reply_keyboard())
        return

    limit_str = message.text.strip()
    if not limit_str.isdigit():
        await message.answer("❌ Iltimos, faqat musbat raqam kiriting (masalan, 500 yoki 0):")
        return

    limit = int(limit_str)
    data = await state.get_data()
    channel_id = data["channel_id"]
    channel_name = data["channel_name"]
    invite_link = data["invite_link"]

    await SubscriptionService(db, bot).add_zayafka_channel(channel_id, channel_name, invite_link, member_limit=limit)
    await state.clear()
    
    limit_info = f"Limit: <b>{limit} ta</b>" if limit > 0 else "Limit: <b>Yo'q (Cheksiz)</b>"
    await message.answer(
        f"✅ Zayafka kanal qo'shildi:\n"
        f"🔐 <b>{escape(channel_name)}</b>  <code>{escape(channel_id)}</code>\n"
        f"⚙️ {limit_info}",
        reply_markup=get_admin_reply_keyboard(),
    )


# ── ❎ Zayafka kanal o'chirish ─────────────────────────────────────────────────

@router.message(or_f(Command("delzayafka"), F.text == BTN_DEL_ZAYAFKA))
async def cmd_del_zayafka(message: Message, state: FSMContext) -> None:
    await state.set_state(DelZayafkaFlow.waiting_channel_id)
    await message.answer(
        "❎ O'chirmoqchi bo'lgan zayafka kanal ID kiriting:\n"
        "Misol: <code>-1001234567890</code>",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(DelZayafkaFlow.waiting_channel_id)
async def flow_del_zayafka(message: Message, state: FSMContext, db: Database, bot: Bot) -> None:
    channel_id = message.text.strip()
    removed = await SubscriptionService(db, bot).remove_zayafka_channel(channel_id)
    await state.clear()
    if removed:
        await message.answer(
            f"✅ Zayafka kanal o'chirildi: <code>{escape(channel_id)}</code>",
            reply_markup=get_admin_reply_keyboard(),
        )
    else:
        await message.answer(
            f"❌ Zayafka kanallar orasida topilmadi: <code>{escape(channel_id)}</code>",
            reply_markup=get_admin_reply_keyboard(),
        )
