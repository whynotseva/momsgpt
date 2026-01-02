from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from app.bot.keyboards.main_menu import main_menu_kb, profile_kb
from app.bot.utils.api_client import api
import os

router = Router()

# Updated Start Handler with User Creation and Terms
@router.message(Command("start"))
async def command_start(message: types.Message):
    # 1. Create user in backend (and Marzban via API)
    username = message.from_user.username or "Anonymous"
    full_name = message.from_user.full_name
    
    # We call API to register user (this will also trigger Marzban sync in backend)
    # Fire and forget or await? Await to ensure user exists before they click buttons.
    await api.create_user(message.from_user.id, username, full_name)
    
    # Welcome with Mom's branding
    text = (
        f"<b>Привет, {full_name}! 👋</b>\n\n"
        "Мы рады видеть тебя в <b>MomsVPN</b> — сервисе, который заботится о твоей свободе и спокойствии.\n\n"
        "🔐 <b>Безопасный. Быстрый. Простой.</b>\n"
        "Мы не храним логи и помогаем тебе быть на связи со всем миром.\n\n"
        "Прежде чем начать, пожалуйста, прими наши правила использования."
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять условия", callback_data="accept_terms")],
        [InlineKeyboardButton(text="📜 Читать правила", url="https://telegra.ph/Terms-of-Service-MomsVPN")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "accept_terms")
async def terms_accept(callback: CallbackQuery):
    await callback.message.delete()
    
    text = (
        "<b>Добро пожаловать домой! 🏠</b>\n\n"
        "Теперь ты часть семьи MomsVPN.\n"
        "Пользуйся интернетом без границ и ограничений.\n\n"
        "👇 <b>Что ты хочешь сделать?</b>"
    )
    
    await callback.message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")

@router.callback_query(F.data == "back_home")
async def back_home_handler(callback: CallbackQuery):
    await callback.message.delete()
    text = (
        "<b>Главное меню 🏠</b>\n\n"
        "Выбери нужный раздел:"
    )
    await callback.message.answer(text, reply_markup=main_menu_kb(), parse_mode="HTML")

# --- PROFILE & SUB-MENUS ---

@router.callback_query(F.data == "profile")
async def profile_handler(callback: CallbackQuery):
    # Show profile menu (where "My Keys" is located)
    sub_info = await api.get_subscription(callback.from_user.id)
    
    status_text = "Не активна"
    if sub_info:
        status_map = {"active": "✅ Активна", "disabled": "❌ Отключена", "limited": "⚠️ Лимит"}
        status_text = status_map.get(sub_info.get("status"), sub_info.get("status", "Не активна"))

    text = (
        "<b>👤 Личный кабинет</b>\n\n"
        f"Ваш ID: <code>{callback.from_user.id}</code>\n"
        f"Статус подписки: <b>{status_text}</b>\n\n"
        "Управляйте подпиской и ключами здесь."
    )
    await callback.message.edit_text(text, reply_markup=profile_kb(), parse_mode="HTML")


@router.callback_query(F.data == "my_keys")
async def my_keys(callback: CallbackQuery):
    from app.bot.utils.crypto import encrypt_vless_link
    from datetime import datetime
    
    # Get user name for personalization
    user_name = callback.from_user.first_name or "друг"
    
    # Fetch real subscription from API
    sub_info = await api.get_subscription(callback.from_user.id)
    
    if not sub_info:
        await callback.answer("Ошибка получения ключа. Попробуйте /start", show_alert=True)
        return

    # Get the subscription URL
    subscription_url = sub_info.get("subscription_url", "")
    if not subscription_url:
        await callback.answer("Ключ ещё не готов. Подождите минуту и попробуйте снова.", show_alert=True)
        return
    
    # Encrypt subscription URL using Happ's official API
    encrypted_key = await encrypt_vless_link(subscription_url)
    
    # Format traffic with progress bar
    used_bytes = sub_info.get("used_traffic") or 0
    data_limit = sub_info.get("data_limit") or 0
    used_gb = round(used_bytes / (1024**3), 2)
    
    if data_limit and data_limit > 0:
        limit_gb = int(round(data_limit / (1024**3), 0))
        percent = min(int((used_bytes / data_limit) * 100), 100)
        # Create visual progress bar
        filled = int(percent / 10)
        empty = 10 - filled
        progress_bar = "▓" * filled + "░" * empty
        traffic_str = f"{progress_bar} {percent}%\n{used_gb} из {limit_gb} ГБ"
    else:
        traffic_str = f"▓░░░░░░░░░ 0%\n{used_gb} ГБ из ∞ (безлимит)"
    
    # Format expiration with days remaining
    expire_ts = sub_info.get("expire") or 0
    if expire_ts and expire_ts > 0:
        expire_date = datetime.fromtimestamp(expire_ts)
        days_left = (expire_date - datetime.now()).days
        if days_left > 0:
            expire_text = f"{expire_date.strftime('%d.%m.%Y')} <i>({days_left} дн.)</i>"
        else:
            expire_text = f"{expire_date.strftime('%d.%m.%Y')} ⚠️"
    else:
        expire_text = "♾️ Бессрочно"
    
    # Status with emoji
    status_map = {
        "active": "🟢 АКТИВЕН",
        "disabled": "🔴 ОТКЛЮЧЕН",
        "limited": "🟡 ЛИМИТ",
        "expired": "⏰ ИСТЁК"
    }
    status_raw = sub_info.get("status", "active")
    status_str = status_map.get(status_raw, status_raw.upper())
    
    # Device info
    last_device = sub_info.get("last_device")
    if last_device:
        device_text = f"📱 {last_device}"
    else:
        device_text = "📱 <i>Ещё не подключались</i>"
    
    # Dynamic server status check
    try:
        server_data = await api.get_server_status()
        if server_data.get("online"):
            server_status = "🟢 NL (Нидерланды) • Online"
        else:
            server_status = "🔴 NL (Нидерланды) • Offline"
    except:
        server_status = "⚪ NL (Нидерланды) • Проверка..."
    
    text = (
        f"Привет, <b>{user_name}</b>! 👋\n\n"
        
        f"━━━━━ <b>СТАТУС</b> ━━━━━\n"
        f"VPN: <b>{status_str}</b>\n"
        f"Действует до: <b>{expire_text}</b>\n\n"
        
        f"━━━━━ <b>ТРАФИК</b> ━━━━━\n"
        f"<code>{traffic_str}</code>\n"
        f"<i>Обновляется 1-го числа месяца</i>\n\n"
        
        f"━━━━━ <b>СЕРВЕР</b> ━━━━━\n"
        f"{server_status}\n\n"
        
        f"━━━━━ <b>УСТРОЙСТВО</b> ━━━━━\n"
        f"{device_text}\n\n"
        
        f"━━━━━ <b>ВАШ КЛЮЧ</b> ━━━━━\n"
        f"<i>Для приложения HAPP • Нажми чтобы скопировать</i>\n"
        f"<blockquote><code>{encrypted_key}</code></blockquote>\n\n"
        
        f"📲 <a href='https://apps.apple.com/app/id6450507239'>Скачать Happ</a> • "
        f"💬 <a href='https://t.me/momsvpn_support'>Поддержка</a>"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Перегенерировать ключ", callback_data="regenerate_key")],
        [
            InlineKeyboardButton(text="« Назад", callback_data="profile"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_home")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)

@router.callback_query(F.data == "regenerate_key")
async def regenerate_key_handler(callback: CallbackQuery):
    """Regenerate user's VPN key - delete and recreate."""
    telegram_id = callback.from_user.id
    username = callback.from_user.username or "User"
    user_name = callback.from_user.first_name or username
    
    # Show loading message
    await callback.message.edit_text("⏳ <b>Перегенерация ключа...</b>\n\nПожалуйста, подождите.", parse_mode="HTML")
    
    try:
        from app.api.services.xray import marzban_service
        from app.bot.utils.crypto import encrypt_vless_link
        
        marzban_username = f"user_{telegram_id}"
        
        # Delete existing user
        await marzban_service.delete_user(marzban_username)
        
        # Create new user
        result = await marzban_service.create_or_update_user(telegram_id, username)
        
        if result:
            await callback.answer("✅ Ключ перегенерирован!", show_alert=True)
            
            # Get new subscription URL and show it
            subscription_url = result.get("subscription_url")
            encrypted_key = await encrypt_vless_link(subscription_url)
            
            text = (
                f"✅ <b>Ключ успешно перегенерирован!</b>\n\n"
                f"━━━━━ <b>НОВЫЙ КЛЮЧ</b> ━━━━━\n"
                f"<i>Скопируй и добавь в Happ:</i>\n"
                f"<blockquote><code>{encrypted_key}</code></blockquote>\n\n"
                f"⚠️ <b>Важно:</b> Удали старую подписку в Happ и добавь новую!"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔑 Мои ключи", callback_data="my_keys")],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="back_home")]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await callback.answer("❌ Ошибка создания ключа", show_alert=True)
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка: {str(e)[:100]}", parse_mode="HTML")

@router.callback_query(F.data == "buy_sub")
async def buy_sub_handler(callback: CallbackQuery):
    await callback.answer("Скоро! Оплата подключается...", show_alert=True)

@router.callback_query(F.data == "referral")
async def referral_handler(callback: CallbackQuery):
    await callback.answer("Раздел в разработке 🏗", show_alert=True)

@router.callback_query(F.data == "change_server")
async def server_handler(callback: CallbackQuery):
    await callback.answer("Пока доступен только один сервер (NL) 🇳🇱", show_alert=True)

