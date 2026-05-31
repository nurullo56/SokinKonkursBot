from html import escape

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.admin_kb import (
    BTN_CANCEL,
    BTN_CLOSE,
    get_admin_keyboard_remove,
    get_admin_reply_keyboard,
)

router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👑 <b>Admin panel</b>\n\n"
        "📊 Statistika — konkurs raqamlari\n"
        "⚙️ Sozlamalar — joriy sozlamalar\n"
        "▶️ Boshlash / ⏹ To'xtatish — konkurs holati\n"
        "🏆 Natijalar — g'oliblarni tanlash\n"
        "📋 Kanallar ro'yxati — majburiy obunalar\n"
        "➕ Kanal qo'shish — ommaviy kanal qo'shish\n"
        "🗑 Kanal o'chirish — ommaviy kanal o'chirish\n"
        "🔐 Zayafka qo'shish — zayafka kanal qo'shish\n"
        "❎ Zayafka o'chirish — zayafka kanal o'chirish\n"
        "🔧 Guruh/Kanal sozlash — guruh va kanal ID larini o'rnatish",
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
