from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from database.connection import Database
from utils.emoji import ce, reload as reload_emojis, _CE
from keyboards.user_kb import (
    BTN_MY_LINK,
    BTN_MY_REFS,
    get_keyboard_remove,
    get_main_inline_keyboard,
    get_phone_keyboard,
    get_subscription_keyboard,
    get_user_reply_keyboard,
)
from services.contest_service import ContestService
from services.referral_service import ReferralService
from services.subscription_service import SubscriptionService

router = Router()



async def _ensure_user(
    db: Database, user_id: int, username: str | None, first_name: str | None
) -> None:
    await db.execute(
        "INSERT OR IGNORE INTO users "
        "(user_id, username, first_name, participated, created_at, updated_at) "
        "VALUES (?, ?, ?, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
        (user_id, username or "", first_name or ""),
    )
    await db.execute(
        "UPDATE users SET username = ?, first_name = ?, updated_at = CURRENT_TIMESTAMP "
        "WHERE user_id = ?",
        (username or "", first_name or "", user_id),
    )
    await db.commit()


async def _notify_referrer(db: Database, bot: Bot, new_user) -> None:
    row = await db.fetchone(
        "SELECT referrer_id FROM referrals WHERE referred_id = ?", (new_user.id,)
    )
    if not row:
        return
    referrer_id = row["referrer_id"]
    count_row = await db.fetchone(
        "SELECT referral_count FROM users WHERE user_id = ?", (referrer_id,)
    )
    count = count_row["referral_count"] if count_row else 0
    full_name = " ".join(filter(None, [new_user.first_name, new_user.last_name])).strip() or new_user.username or str(new_user.id)
    try:
        await bot.send_message(
            referrer_id,
            f"{ce('🎉')} Sizning havolangiz orqali <b>{full_name}</b> ro'yxatdan o'tdi!\n\n"
            f"{ce('👥')} Taklif qilganlaringiz: <b>{count}/5</b>",
        )
    except Exception:
        pass


async def _notify_admins(db: Database, bot: Bot, user: object) -> None:
    admin_ids_str = await db.get_setting("admin_ids") or ""
    admin_ids = [
        int(x.strip()) for x in admin_ids_str.split(",") if x.strip().lstrip("-").isdigit()
    ]
    full_name = " ".join(filter(None, [user.first_name, user.last_name])).strip() or user.username or str(user.id)
    username_part = f" (@{user.username})" if user.username else ""
    text = f"✅ Yangi ishtirokchi ro'yxatdan o'tdi!\n\n👤 {full_name}{username_part}\n🆔 <code>{user.id}</code>"
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            pass


async def _show_main(message: Message, db: Database, bot: Bot, bot_username: str, user_id: int) -> None:
    sub_svc = SubscriptionService(db, bot)
    unsubscribed = await sub_svc.get_unsubscribed(user_id)
    if unsubscribed:
        await message.reply(
            sub_svc.build_prompt_text(unsubscribed),
            reply_markup=get_subscription_keyboard(unsubscribed),
        )
        return

    bot_mode = await db.get_setting("bot_mode") or "BOT"

    if bot_mode == "CHANNEL":
        user_row = await db.fetchone(
            "SELECT verified, contest_number FROM users WHERE user_id = ?", (user_id,)
        )
        if not user_row:
            await message.reply("❌ Xatolik yuz berdi. /start bosing.")
            return
        verified = user_row.get("verified") or False
        contest_number = user_row.get("contest_number")
        if not verified or not contest_number:
            contest_number = await ContestService(db).verify_user(user_id)
        text = (
            f"{ce('🎉')} <b>Kanal konkursiga xush kelibsiz!</b>\n\n"
            f"{ce('✅')} Siz barcha homiy kanallarga obuna bo'ldingiz va konkursda ro'yxatdan o'tdingiz!\n\n"
            f"🎫 Sizning konkurs raqamingiz: <b>{contest_number}</b>\n\n"
            "📣 Konkurs natijalari kanalda e'lon qilinadi. Obunani o'chirmang!"
        )
    else:
        count = await ReferralService(db).get_referral_count(user_id)
        group_id = await db.get_setting("group_id") or "guruh_belgilanmagan"
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        text = (
            f"{ce('🎉')} Konkursga xush kelibsiz!\n\n"
            f"{ce('📃')} Qoidalar:\n"
            f"{ce('1️⃣')} 5 ta do'stingizni botga taklif qiling\n"
            f"{ce('2️⃣')} Barcha do'stlaringiz /start bosishi kerak\n"
            f"{ce('3️⃣')} 5 ta odam to'plab, statistikangizni skrinshot qiling\n"
            f"{ce('4️⃣')} Skrinshotni guruhga tashlang: {group_id}\n"
            f"{ce('5️⃣')} Bot tekshiradi va raqam beradi!\n\n"
            f"{ce('👥')} Hozirgi taklif qilganlaringiz: {count}/5\n"
            f"{ce('🔗')} Sizning havolangiz:\n<code>{ref_link}</code>"
        )

    await message.reply(text, reply_markup=get_user_reply_keyboard())

    result = await db.execute(
        "UPDATE users SET welcomed = TRUE WHERE user_id = ? AND welcomed = FALSE", (user_id,)
    )
    await db.commit()
    if result.rowcount > 0:
        await _notify_admins(db, bot, message.from_user)
        await _notify_referrer(db, bot, message.from_user)




@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, bot: Bot, bot_username: str) -> None:
    user = message.from_user
    await _ensure_user(db, user.id, user.username, user.first_name)

    parts = message.text.split(maxsplit=1)
    if len(parts) > 1 and parts[1].startswith("ref_"):
        ref_str = parts[1][4:]
        if ref_str.isdigit():
            referrer_id = int(ref_str)
            if referrer_id != user.id:
                referrer = await db.fetchone(
                    "SELECT user_id FROM users WHERE user_id = ?", (referrer_id,)
                )
                if referrer:
                    await ReferralService(db).add_referral(referrer_id, user.id)

    row = await db.fetchone("SELECT phone FROM users WHERE user_id = ?", (user.id,))
    if not row or not row.get("phone"):
        await message.reply(
            f"{ce('📱')} Botdan foydalanish uchun telefon raqamingizni ulashing:",
            reply_markup=get_phone_keyboard(),
        )
        return

    await _show_main(message, db, bot, bot_username, user.id)


@router.message(F.contact)
async def handle_contact(message: Message, db: Database, bot: Bot, bot_username: str) -> None:
    contact = message.contact
    if contact.user_id is not None and contact.user_id != message.from_user.id:
        await message.reply("❌ Faqat o'z raqamingizni ulashing.")
        return

    await db.execute(
        "UPDATE users SET phone = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
        (contact.phone_number, message.from_user.id),
    )
    await db.commit()

    await message.reply(f"{ce('✅')} Telefon raqam saqlandi!", reply_markup=get_keyboard_remove())
    await _show_main(message, db, bot, bot_username, message.from_user.id)


@router.message(F.text == BTN_MY_LINK)
async def btn_my_link(message: Message, db: Database, bot_username: str) -> None:
    user_id = message.from_user.id
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    count = await ReferralService(db).get_referral_count(user_id)

    await message.reply(
        f"{ce('🔗')} <b>Sizning referal havolangiz:</b>\n\n"
        f"<code>{ref_link}</code>\n\n"
        f"{ce('👥')} Taklif qilganlar: <b>{count}/5</b>"
    )


@router.message(F.text == BTN_MY_REFS)
async def btn_my_refs(message: Message, db: Database) -> None:
    user_id = message.from_user.id

    row = await db.fetchone(
        "SELECT referral_count, verified, contest_number FROM users WHERE user_id = ?",
        (user_id,),
    )
    if not row:
        await message.reply("Ma'lumot topilmadi. /start bosing.")
        return

    count: int = row["referral_count"]
    verified: bool = row["verified"]
    contest_number = row["contest_number"]

    if count >= 5:
        status = f"{ce('✅')} Tayyor! Skrinshotni guruhga yuboring."
    else:
        status = f"{ce('⌛')} Yana {5 - count} ta do'st kerak"

    lines = [
        f"{ce('👥')} <b>Referallar statistikasi:</b>\n",
        f"{ce('📊')} Taklif qilganlar: <b>{count}/5</b>",
        f"{ce('📌')} Holat: {status}",
    ]

    if verified and contest_number:
        lines.append(f"{ce('✅')} Konkurs raqamingiz: <b>{contest_number}</b>")

    await message.reply("\n".join(lines), reply_markup=get_main_inline_keyboard())


@router.callback_query(F.data == "my_friends")
async def my_friends_callback(callback: CallbackQuery, db: Database) -> None:
    user_id = callback.from_user.id

    referred_rows = await db.fetchall(
        "SELECT u.first_name, u.username FROM referrals r "
        "JOIN users u ON u.user_id = r.referred_id "
        "WHERE r.referrer_id = ? ORDER BY r.created_at",
        (user_id,),
    )

    if referred_rows:
        lines = [f"{ce('👥')} <b>Do'stlar ro'yxati ({len(referred_rows)} ta):</b>\n"]
        for i, r in enumerate(referred_rows[:20], 1):
            name = (r.get("first_name") or "").strip() or r.get("username") or "Noma'lum"
            lines.append(f"  {i}. {name}")
        if len(referred_rows) > 20:
            lines.append(f"  … va yana {len(referred_rows) - 20} ta")
    else:
        lines = [f"{ce('👥')} <b>Do'stlar ro'yxati:</b>\n", "<i>Hali hech kim taklif qilinmagan.</i>"]

    try:
        await callback.message.edit_text("\n".join(lines))
    except Exception:
        await callback.message.answer("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data.startswith("zayafka_joined:"))
async def zayafka_joined_callback(callback: CallbackQuery, db: Database) -> None:
    channel_id = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id
    await db.execute(
        "INSERT OR IGNORE INTO zayafka_join_requests (user_id, channel_id) VALUES (?, ?)",
        (user_id, channel_id),
    )
    await db.commit()
    await callback.answer("✅ Qabul qilindi! Endi 'Obunani tekshirish' ni bosing.", show_alert=False)


@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    await callback.answer()
    user_id = callback.from_user.id
    sub_svc = SubscriptionService(db, bot)
    try:
        unsubscribed = await sub_svc.get_unsubscribed(user_id)

        if not unsubscribed:
            bot_mode = await db.get_setting("bot_mode") or "BOT"
            if bot_mode == "CHANNEL":
                user_row = await db.fetchone(
                    "SELECT verified, contest_number FROM users WHERE user_id = ?", (user_id,)
                )
                if not user_row:
                    await callback.message.edit_text("❌ Xatolik yuz berdi. /start bosing.")
                    return
                verified = user_row.get("verified") or False
                contest_number = user_row.get("contest_number")
                if not verified or not contest_number:
                    contest_number = await ContestService(db).verify_user(user_id)
                await callback.message.edit_text(
                    f"{ce('🎉')} <b>Kanal konkursiga xush kelibsiz!</b>\n\n"
                    f"{ce('✅')} Barcha kanallarga obuna bo'ldingiz va ro'yxatdan o'tdingiz!\n\n"
                    f"🎫 Sizning konkurs raqamingiz: <b>{contest_number}</b>\n\n"
                    "📣 Konkurs natijalari kanalda e'lon qilinadi. Kanallardan chiqib ketmang!",
                )
                result = await db.execute(
                    "UPDATE users SET welcomed = TRUE WHERE user_id = ? AND welcomed = FALSE", (user_id,)
                )
                await db.commit()
                if result.rowcount > 0:
                    await _notify_admins(db, bot, callback.from_user)
            else:
                await callback.message.edit_text(
                    f"{ce('✅')} Ajoyib! Siz barcha kanallarga obuna bo'ldingiz.\n\n"
                    "Endi /start buyrug'ini yuboring.",
                )
            return

        text = sub_svc.build_prompt_text(unsubscribed)
        keyboard = get_subscription_keyboard(unsubscribed)
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)

    except Exception:
        try:
            await callback.message.edit_text("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
        except Exception:
            pass


