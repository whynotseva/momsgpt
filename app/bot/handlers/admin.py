"""
Admin Handler - Telegram bot admin commands.
/admin command with inline keyboard for management.
Enhanced with user details, traffic/days management.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import logging
from datetime import datetime, timedelta

from app.bot.utils.api_client import APIClient

router = Router()
logger = logging.getLogger(__name__)

# Admin IDs (can be moved to .env)
ADMIN_IDS = [44054166]  # Add your Telegram ID


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in ADMIN_IDS


def extract_tg_username(user: dict) -> str:
    """Extract Telegram username from Marzban note field.
    Note format: 'TG ID: 123456 (username)'
    """
    import re
    note = user.get("note", "")
    if note:
        # Try to extract username from note
        match = re.search(r'\(([^)]+)\)', note)
        if match:
            username = match.group(1)
            if username and username != "User":
                return f"@{username}"
    # Fallback to internal username
    return user.get("username", "unknown")


class AdminStates(StatesGroup):
    """Admin FSM states for input."""
    waiting_add_days = State()
    waiting_add_traffic = State()
    current_username = State()


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Main admin menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin:users:0")],
        [InlineKeyboardButton(text="🖥️ Сервер", callback_data="admin:server")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin:close")]
    ])


@router.message(Command("admin"))
async def admin_command(message: Message):
    """Admin panel entry point."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён")
        return
    
    text = """
🔐 <b>Админ-панель MomsVPN</b>

Выберите раздел:
"""
    await message.answer(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery):
    """Show statistics."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    api = APIClient()
    try:
        # Get server status
        server = await api.get_server_status()
        
        # Get all users from Marzban via direct call
        from app.api.services.xray import marzban_service
        users = await marzban_service.get_all_users()
        
        total_users = len(users) if users else 0
        active_users = sum(1 for u in users if u.get("status") == "active") if users else 0
        disabled_users = sum(1 for u in users if u.get("status") == "disabled") if users else 0
        total_traffic = sum(u.get("used_traffic", 0) for u in users) if users else 0
        total_traffic_gb = round(total_traffic / (1024**3), 2)
        
        online_users = server.get("online_users", 0) if server.get("online") else 0
        server_status = "🟢 Online" if server.get("online") else "🔴 Offline"
        
        text = f"""
📊 <b>Статистика MomsVPN</b>

👥 <b>Пользователи:</b>
├ Всего: <b>{total_users}</b>
├ Активных: <b>{active_users}</b>
├ Заблокированных: <b>{disabled_users}</b>
└ Онлайн сейчас: <b>{online_users}</b>

📊 <b>Трафик:</b>
└ Использовано: <b>{total_traffic_gb} ГБ</b>

🖥️ <b>Сервер:</b> {server_status}
"""
    except Exception as e:
        text = f"❌ Ошибка получения статистики: {e}"
    finally:
        await api.close()
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:stats")],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data="admin:menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin:users:"))
async def admin_users(callback: CallbackQuery):
    """Show users list with pagination."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    # Get page number from callback data
    page = int(callback.data.split(":")[2])
    per_page = 8
    
    try:
        from app.api.services.xray import marzban_service
        users = await marzban_service.get_all_users()
        
        if not users:
            text = "👥 Пользователей нет"
            await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Меню", callback_data="admin:menu")]
            ]), parse_mode="HTML")
            return
        
        # Pagination
        total = len(users)
        total_pages = (total + per_page - 1) // per_page
        start = page * per_page
        end = start + per_page
        page_users = users[start:end]
        
        text = f"👥 <b>Пользователи</b> ({page + 1}/{total_pages})\n\nНажмите для управления:"
        
        # User buttons
        buttons = []
        for user in page_users:
            status_emoji = {"active": "🟢", "disabled": "🔴", "limited": "🟡", "expired": "⏰"}
            emoji = status_emoji.get(user.get("status"), "❓")
            internal_name = user.get("username", "unknown")
            display_name = extract_tg_username(user)
            used_gb = round(user.get("used_traffic", 0) / (1024**3), 1)
            buttons.append([
                InlineKeyboardButton(
                    text=f"{emoji} {display_name} ({used_gb} ГБ)",
                    callback_data=f"user:{internal_name}"
                )
            ])
        
        # Navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin:users:{page - 1}"))
        nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin:users:{page + 1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        buttons.append([InlineKeyboardButton(text="⬅️ Меню", callback_data="admin:menu")])
        
        await callback.message.edit_text(
            text, 
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), 
            parse_mode="HTML"
        )
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("user:") & ~F.data.startswith("user:action:"))
async def user_detail(callback: CallbackQuery):
    """Show user details with actions."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    username = callback.data.split(":")[1]
    
    from app.api.services.xray import marzban_service
    user = await marzban_service.get_user(username)
    
    if not user:
        await callback.answer(f"❌ Пользователь не найден", show_alert=True)
        return
    
    # Format user info
    status_emoji = {"active": "🟢", "disabled": "🔴", "limited": "🟡", "expired": "⏰"}
    emoji = status_emoji.get(user.get("status"), "❓")
    
    used_traffic = user.get("used_traffic", 0)
    data_limit = user.get("data_limit", 0)
    used_gb = round(used_traffic / (1024**3), 2)
    limit_gb = round(data_limit / (1024**3), 0) if data_limit else "∞"
    
    # Calculate percentage
    if data_limit and data_limit > 0:
        percent = min(100, round(used_traffic / data_limit * 100))
        progress = "▓" * (percent // 10) + "░" * (10 - percent // 10)
    else:
        percent = 0
        progress = "░" * 10
    
    # Expiration
    expire = user.get("expire")
    if expire:
        expire_date = datetime.fromtimestamp(expire)
        days_left = (expire_date - datetime.now()).days
        expire_str = f"{expire_date.strftime('%d.%m.%Y')} ({days_left} дн.)"
    else:
        expire_str = "♾️ Бессрочно"
    
    # Online status
    online_at = user.get("online_at")
    if online_at:
        online_date = datetime.fromisoformat(online_at.replace("Z", "+00:00"))
        online_str = online_date.strftime("%d.%m.%Y %H:%M")
    else:
        online_str = "Никогда"
    
    # Extract telegram info from note
    tg_id = username.replace("user_", "") if username.startswith("user_") else "N/A"
    display_name = extract_tg_username(user)
    
    text = f"""
👤 <b>{display_name}</b>

📱 <b>Telegram ID:</b> <code>{tg_id}</code>
🔗 <b>Внутренний ID:</b> <code>{username}</code>
{emoji} <b>Статус:</b> {user.get("status")}

📊 <b>Трафик:</b>
{progress} {percent}%
{used_gb} ГБ / {limit_gb} ГБ

📅 <b>Подписка:</b> {expire_str}
🕐 <b>Последний онлайн:</b> {online_str}

<i>Выберите действие:</i>
"""
    
    # Action buttons
    buttons = []
    
    # Block/Unblock
    if user.get("status") == "active":
        buttons.append([InlineKeyboardButton(text="🔒 Заблокировать", callback_data=f"user:action:block:{username}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔓 Разблокировать", callback_data=f"user:action:unblock:{username}")])
    
    # Traffic and Days
    buttons.append([
        InlineKeyboardButton(text="📊 + Трафик", callback_data=f"user:action:addtraffic:{username}"),
        InlineKeyboardButton(text="📅 + Дни", callback_data=f"user:action:adddays:{username}")
    ])
    
    # Reset traffic
    buttons.append([InlineKeyboardButton(text="🔄 Сбросить трафик", callback_data=f"user:action:reset:{username}")])
    
    # Back
    buttons.append([InlineKeyboardButton(text="⬅️ К списку", callback_data="admin:users:0")])
    
    await callback.message.edit_text(
        text, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), 
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("user:action:"))
async def user_action(callback: CallbackQuery, state: FSMContext):
    """Handle user actions."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    parts = callback.data.split(":")
    action = parts[2]
    username = parts[3]
    
    from app.admin.services.marzban import MarzbanAdminService
    
    try:
        if action == "block":
            await MarzbanAdminService.disable_user(username)
            await callback.answer("✅ Пользователь заблокирован", show_alert=True)
            # Refresh user detail
            callback.data = f"user:{username}"
            await user_detail(callback)
            
        elif action == "unblock":
            await MarzbanAdminService.enable_user(username)
            await callback.answer("✅ Пользователь разблокирован", show_alert=True)
            callback.data = f"user:{username}"
            await user_detail(callback)
            
        elif action == "reset":
            await MarzbanAdminService.reset_user_traffic(username)
            await callback.answer("✅ Трафик сброшен", show_alert=True)
            callback.data = f"user:{username}"
            await user_detail(callback)
            
        elif action == "adddays":
            await state.update_data(current_username=username)
            await state.set_state(AdminStates.waiting_add_days)
            
            buttons = [
                [
                    InlineKeyboardButton(text="7 дней", callback_data=f"add:days:7:{username}"),
                    InlineKeyboardButton(text="30 дней", callback_data=f"add:days:30:{username}")
                ],
                [
                    InlineKeyboardButton(text="90 дней", callback_data=f"add:days:90:{username}"),
                    InlineKeyboardButton(text="365 дней", callback_data=f"add:days:365:{username}")
                ],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"user:{username}")]
            ]
            
            await callback.message.edit_text(
                f"📅 <b>Добавить дни к подписке</b>\n\nПользователь: <code>{username}</code>\n\nВыберите количество дней:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                parse_mode="HTML"
            )
            
        elif action == "addtraffic":
            await state.update_data(current_username=username)
            await state.set_state(AdminStates.waiting_add_traffic)
            
            buttons = [
                [
                    InlineKeyboardButton(text="+10 ГБ", callback_data=f"add:traffic:10:{username}"),
                    InlineKeyboardButton(text="+50 ГБ", callback_data=f"add:traffic:50:{username}")
                ],
                [
                    InlineKeyboardButton(text="+100 ГБ", callback_data=f"add:traffic:100:{username}"),
                    InlineKeyboardButton(text="+300 ГБ", callback_data=f"add:traffic:300:{username}")
                ],
                [InlineKeyboardButton(text="❌ Отмена", callback_data=f"user:{username}")]
            ]
            
            await callback.message.edit_text(
                f"📊 <b>Добавить трафик</b>\n\nПользователь: <code>{username}</code>\n\nВыберите объём:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                parse_mode="HTML"
            )
            
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {e}", show_alert=True)


@router.callback_query(F.data.startswith("add:days:"))
async def add_days(callback: CallbackQuery, state: FSMContext):
    """Add days to subscription."""
    if not is_admin(callback.from_user.id):
        return
    
    parts = callback.data.split(":")
    days = int(parts[2])
    username = parts[3]
    
    from app.admin.services.marzban import MarzbanAdminService
    
    try:
        success = await MarzbanAdminService.extend_user(username, days)
        if success:
            await callback.answer(f"✅ Добавлено {days} дней!", show_alert=True)
        else:
            await callback.answer("❌ Ошибка добавления дней", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)
    
    await state.clear()
    callback.data = f"user:{username}"
    await user_detail(callback)


@router.callback_query(F.data.startswith("add:traffic:"))
async def add_traffic(callback: CallbackQuery, state: FSMContext):
    """Add traffic to user."""
    if not is_admin(callback.from_user.id):
        return
    
    parts = callback.data.split(":")
    gb = int(parts[2])
    username = parts[3]
    
    try:
        from app.api.services.xray import marzban_service
        
        # Get current user
        user = await marzban_service.get_user(username)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Calculate new limit
        current_limit = user.get("data_limit", 0)
        add_bytes = gb * (1024 ** 3)
        new_limit = current_limit + add_bytes
        
        # Update via Marzban API
        import httpx
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            headers = await marzban_service._get_headers()
            resp = await client.put(
                f"{marzban_service.base_url}/api/user/{username}",
                headers=headers,
                json={"data_limit": new_limit}
            )
            
            if resp.status_code == 200:
                await callback.answer(f"✅ Добавлено {gb} ГБ!", show_alert=True)
            else:
                await callback.answer("❌ Ошибка добавления трафика", show_alert=True)
                
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)
    
    await state.clear()
    callback.data = f"user:{username}"
    await user_detail(callback)


@router.callback_query(F.data == "admin:server")
async def admin_server(callback: CallbackQuery):
    """Show server status."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    api = APIClient()
    try:
        server = await api.get_server_status()
        
        if server.get("online"):
            cpu = server.get("cpu_usage", 0)
            mem = server.get("mem_usage", 0)
            
            # CPU bar
            cpu_bar = "▓" * (int(cpu) // 10) + "░" * (10 - int(cpu) // 10)
            mem_bar = "▓" * (int(mem) // 10) + "░" * (10 - int(mem) // 10)
            
            text = f"""
🖥️ <b>Статус сервера</b>

🇳🇱 <b>Нидерланды</b>
├ Статус: 🟢 Online
├ Онлайн: <b>{server.get("online_users", 0)}</b> пользователей
│
├ 💻 CPU: {cpu_bar} {cpu}%
└ 🧠 RAM: {mem_bar} {mem}%
"""
        else:
            text = "🖥️ <b>Сервер</b>\n\n🔴 Недоступен"
    except Exception as e:
        text = f"❌ Ошибка: {e}"
    finally:
        await api.close()
    
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:server")],
        [InlineKeyboardButton(text="⬅️ Меню", callback_data="admin:menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_kb, parse_mode="HTML")


@router.callback_query(F.data == "admin:menu")
async def admin_menu(callback: CallbackQuery):
    """Return to admin menu."""
    if not is_admin(callback.from_user.id):
        return
    
    text = """
🔐 <b>Админ-панель MomsVPN</b>

Выберите раздел:
"""
    await callback.message.edit_text(text, reply_markup=admin_menu_keyboard(), parse_mode="HTML")


@router.callback_query(F.data == "admin:close")
async def admin_close(callback: CallbackQuery):
    """Close admin panel."""
    await callback.message.delete()


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    """Do nothing (for pagination counter)."""
    await callback.answer()
