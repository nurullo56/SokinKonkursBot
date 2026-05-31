from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


# ── Button text constants ────────────────────────────────────────────────────
BTN_MY_LINK     = "🔗 Referal havolam"
BTN_MY_REFS     = "👥 Referallarim"


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_keyboard_remove() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def get_user_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_MY_LINK), KeyboardButton(text=BTN_MY_REFS)],
        ],
        resize_keyboard=True,
    )



def get_main_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Mening do'stlarim", callback_data="my_friends")]
        ]
    )


def get_subscription_keyboard(unsubscribed: list[dict] | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for ch in (unsubscribed or []):
        link = ch.get("link", "")
        if ch["type"] == "public":
            if link:
                rows.append([InlineKeyboardButton(text=f"📢 {ch['name']}", url=link)])
        else:
            channel_id = ch.get("channel_id", "")
            row = []
            if link:
                row.append(InlineKeyboardButton(text=f"🔐 {ch['name']}", url=link))
            if channel_id:
                row.append(InlineKeyboardButton(
                    text="✅ So'rov yubordim",
                    callback_data=f"zayafka_joined:{channel_id}",
                ))
            if row:
                rows.append(row)
    rows.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
