from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# ── Button text constants ────────────────────────────────────────────────────
BTN_STATS        = "📊 Statistika"
BTN_SETTINGS     = "⚙️ Sozlamalar"
BTN_START        = "▶️ Konkursni boshlash"
BTN_STOP         = "⏹ Konkursni to'xtatish"
BTN_TOGGLE_MODE  = "🔄 Rejimni almashtirish"
BTN_BROADCAST    = "📢 Reklama tarqatish"
BTN_RESULTS      = "🏆 Natijalar"
BTN_CHANNELS     = "📋 Kanallar ro'yxati"
BTN_ADD_PUBLIC   = "➕ Kanal qo'shish"
BTN_DEL_PUBLIC   = "🗑 Kanal o'chirish"
BTN_ADD_ZAYAFKA  = "🔐 Zayafka qo'shish"
BTN_DEL_ZAYAFKA  = "❎ Zayafka o'chirish"
BTN_SETUP        = "🔧 Guruh/Kanal sozlash"
BTN_CLOSE        = "❌ Panelni yopish"
BTN_CANCEL       = "🚫 Bekor qilish"


def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_STATS),       KeyboardButton(text=BTN_SETTINGS)],
            [KeyboardButton(text=BTN_START),        KeyboardButton(text=BTN_STOP)],
            [KeyboardButton(text=BTN_TOGGLE_MODE),  KeyboardButton(text=BTN_BROADCAST)],
            [KeyboardButton(text=BTN_RESULTS),      KeyboardButton(text=BTN_CHANNELS)],
            [KeyboardButton(text=BTN_ADD_PUBLIC),   KeyboardButton(text=BTN_DEL_PUBLIC)],
            [KeyboardButton(text=BTN_ADD_ZAYAFKA),  KeyboardButton(text=BTN_DEL_ZAYAFKA)],
            [KeyboardButton(text=BTN_SETUP)],
            [KeyboardButton(text=BTN_CLOSE)],
        ],
        resize_keyboard=True,
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def get_admin_keyboard_remove() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


