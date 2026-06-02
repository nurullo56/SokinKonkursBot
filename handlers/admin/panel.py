import asyncio
import json
import os
from html import escape

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.admin_kb import (
    BTN_CANCEL,
    BTN_CLOSE,
    get_admin_keyboard_remove,
    get_admin_reply_keyboard,
)
from utils.emoji import ce, reload as reload_emojis

EMOJI_JSON = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "custom_emojis.json"))
_emoji_write_lock = asyncio.Lock()

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👑 <b>Admin panel</b>\n\nQaysi amalni bajarmoqchisiz?",
        reply_markup=get_admin_reply_keyboard(),
    )


@router.message(F.text == BTN_CLOSE)
async def btn_close(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Admin paneldan chiqdingiz.", reply_markup=get_admin_keyboard_remove())


@router.message(F.text == BTN_CANCEL)
async def btn_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=get_admin_reply_keyboard())


@router.message(F.forward_from_chat)
async def get_forwarded_channel_id(message: Message) -> None:
    chat = message.forward_from_chat
    lines = [
        "📋 <b>Kanal ma'lumotlari:</b>\n",
        f"🆔 ID: <code>{chat.id}</code>",
        f"📌 Nomi: <b>{escape(chat.title or 'N/A')}</b>",
        f"📂 Turi: {chat.type}",
    ]
    if chat.username:
        lines.append(f"🔗 Link: @{chat.username}")
    lines.append("\n💡 ID ni nusxalab sozlamalarda foydalaning.")
    await message.reply("\n".join(lines))


# Faqat hech qanday FSM state bo'lmaganda custom emoji larni saqlaydi
@router.message(
    StateFilter(None),
    F.entities.func(lambda ents: any(e.type == "custom_emoji" for e in ents))
)
async def catch_custom_emoji(message: Message) -> None:
    found = {
        message.text[e.offset:e.offset + e.length]: e.custom_emoji_id
        for e in (message.entities or [])
        if e.type == "custom_emoji"
    }
    if not found:
        return

    async with _emoji_write_lock:
        data: dict = {}
        if os.path.exists(EMOJI_JSON):
            with open(EMOJI_JSON, encoding="utf-8") as f:
                data = json.load(f)
        data.update(found)
        with open(EMOJI_JSON, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        reload_emojis()

    lines = [f"{emoji}  =>  {eid}" for emoji, eid in found.items()]
    await message.reply(
        f"{ce('✅')} Saqlandi! ({len(found)} ta)\n\n" + "\n".join(lines)
    )
