from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡️ Подключиться", callback_data="buy_sub")
        ],
        [
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
            InlineKeyboardButton(text="🎁 Партнерка", callback_data="referral")
        ],
        [
            InlineKeyboardButton(text="🆘 Поддержка", url="https://t.me/your_support_user")
        ]
    ])

def profile_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔑 Мои ключи", callback_data="my_keys")
        ],
        [
            InlineKeyboardButton(text="🌍 Сменить сервер", callback_data="change_server"),
            InlineKeyboardButton(text="💳 Продлить", callback_data="buy_sub")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_home")
        ]
    ])
