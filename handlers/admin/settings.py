import logging
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, or_f
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database.connection import Database
from keyboards.admin_kb import (
    BTN_CANCEL,
    BTN_SETTINGS,
    BTN_SETUP,
    BTN_START,
    BTN_STATS,
    BTN_STOP,
    BTN_TOGGLE_MODE,
    get_admin_reply_keyboard,
    get_cancel_keyboard,
)
from services.contest_service import ContestService
from states.admin import SetupWizard

logger = logging.getLogger(__name__)
router = Router()



@router.message(or_f(Command("setup"), F.text == BTN_SETUP))
async def cmd_setup(message: Message, state: FSMContext) -> None:
    await state.set_state(SetupWizard.waiting_group_id)
    await message.answer(
        "Guruh ID kiriting (masalan: -1001234567890):",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(SetupWizard.waiting_group_id)
async def wizard_group_id(message: Message, state: FSMContext, db: Database) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_reply_keyboard())
        return
    group_id = message.text.strip()
    await state.update_data(group_id=group_id)
    await db.set_setting("group_id", group_id)
    await state.set_state(SetupWizard.waiting_channel_id)
    await message.answer("Kanal ID kiriting (masalan: -1009876543210):")


@router.message(SetupWizard.waiting_channel_id)
async def wizard_channel_id(message: Message, state: FSMContext, db: Database) -> None:
    if message.text == BTN_CANCEL:
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=get_admin_reply_keyboard())
        return
    channel_id = message.text.strip()
    data = await state.get_data()
    group_id = data.get("group_id", "N/A")
    await db.set_setting("channel_id", channel_id)
    await state.clear()
    await message.answer(
        f"✅ Sozlamalar saqlandi!\n\n"
        f"👥 Guruh ID: <code>{escape(group_id)}</code>\n"
        f"📢 Kanal ID: <code>{escape(channel_id)}</code>",
        reply_markup=get_admin_reply_keyboard(),
    )


@router.message(Command("setgroup"))
async def cmd_setgroup(message: Message, command: CommandObject, db: Database) -> None:
    if not command.args:
        await message.answer("Foydalanish: /setgroup GROUP_ID")
        return
    group_id = command.args.strip()
    await db.set_setting("group_id", group_id)
    await message.answer(f"✅ Guruh ID saqlandi: <code>{escape(group_id)}</code>")


@router.message(Command("setchannel"))
async def cmd_setchannel(message: Message, command: CommandObject, db: Database) -> None:
    if not command.args:
        await message.answer("Foydalanish: /setchannel CHANNEL_ID")
        return
    channel_id = command.args.strip()
    await db.set_setting("channel_id", channel_id)
    await message.answer(f"✅ Kanal ID saqlandi: <code>{escape(channel_id)}</code>")


@router.message(F.text == BTN_TOGGLE_MODE)
async def cmd_toggle_mode(message: Message, db: Database) -> None:
    current = await db.get_setting("bot_mode") or "BOT"
    new_mode = "CHANNEL" if current == "BOT" else "BOT"
    await db.set_setting("bot_mode", new_mode)
    
    mode_names = {
        "BOT": "Bot Konkursi (Do'stlarni taklif qilish + skrinshot) 🤖",
        "CHANNEL": "Kanal Konkursi (Sponsor kanallarga obuna bo'lish kifoya) 📢"
    }
    await message.answer(
        f"🔄 Bot rejimi almashtirildi!\n\n"
        f"Joriy faol rejim:\n<b>{mode_names[new_mode]}</b>"
    )


@router.message(or_f(Command("settings"), F.text == BTN_SETTINGS))
async def cmd_settings(message: Message, db: Database) -> None:
    group_id   = escape(await db.get_setting("group_id")   or "Belgilanmagan")
    channel_id = escape(await db.get_setting("channel_id") or "Belgilanmagan")
    admin_ids  = escape(await db.get_setting("admin_ids")  or "Belgilanmagan")
    contest_active = (await db.get_setting("contest_active")) == "TRUE"
    status_text = "Faol ✅" if contest_active else "To'xtatilgan ❌"
    
    bot_mode = await db.get_setting("bot_mode") or "BOT"
    mode_text = "🤖 Bot ichida konkurs" if bot_mode == "BOT" else "📢 Kanal homiyligi / konkursi"
    
    stats = await ContestService(db).get_stats()

    await message.answer(
        "⚙️ <b>Bot sozlamalari:</b>\n\n"
        f"👥 Guruh ID: <code>{group_id}</code>\n"
        f"📢 Kanal ID: <code>{channel_id}</code>\n"
        f"👑 Adminlar: <code>{admin_ids}</code>\n"
        f"🔄 Bot rejimi: <b>{mode_text}</b>\n"
        f"📊 Konkurs holati: {status_text}\n"
        f"Ishtirokchilar: {stats['total']}\n"
        f"Tasdiqlangan: {stats['verified']}"
    )


@router.message(or_f(Command("start_contest"), F.text == BTN_START))
async def cmd_start_contest(message: Message, db: Database) -> None:
    await db.set_setting("contest_active", "TRUE")
    await message.answer("✅ Konkurs boshlandi!")


@router.message(or_f(Command("stop_contest"), F.text == BTN_STOP))
async def cmd_stop_contest(message: Message, db: Database) -> None:
    await db.set_setting("contest_active", "FALSE")
    await message.answer("⏹ Konkurs to'xtatildi.")


@router.message(or_f(Command("stats"), F.text == BTN_STATS))
async def cmd_stats(message: Message, db: Database) -> None:
    stats = await ContestService(db).get_stats()
    lines = [
        "📊 <b>Konkurs statistikasi:</b>\n",
        f"👥 Jami ishtirokchilar: {stats['total']}",
        f"✅ Tasdiqlangan: {stats['verified']}",
        f"⏳ Kutilayotganlar (5+ referral): {stats['pending']}",
    ]
    if stats["top_referrers"]:
        lines.append("\n🏅 Top 5 referrerlar:")
        for i, u in enumerate(stats["top_referrers"], 1):
            name = escape(u.get("first_name") or str(u["user_id"]))
            lines.append(f"  {i}. {name} — {u['referral_count']} ta")
    await message.answer("\n".join(lines))
