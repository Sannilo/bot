import requests
from loguru import logger
from datetime import datetime
from bd import DatabaseManager

COUNTRY_FLAGS = {
    'Германия': '🇩🇪', 'Germany': '🇩🇪',
    'Нидерланды': '🇳🇱', 'Netherlands': '🇳🇱',
    'США': '🇺🇸', 'USA': '🇺🇸',
    'Великобритания': '🇬🇧', 'UK': '🇬🇧',
    'Франция': '🇫🇷', 'France': '🇫🇷',
}

def get_country_flag(server_name: str) -> str:
    """Gets a country flag emoji based on the server name."""
    if not server_name:
        return ''
    for country, flag in COUNTRY_FLAGS.items():
        if country in server_name:
            return flag
    return '🌍'

def send_telegram_message(bot_token: str, chat_id: str, text: str, parse_mode: str = "HTML"):
    """Sends a message to a Telegram user or channel."""
    if not bot_token or not chat_id:
        logger.error("Notifier: Bot token or chat ID is missing.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': parse_mode, 'disable_web_page_preview': True}

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Notification sent to {chat_id}.")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send notification to {chat_id}. Error: {e}")
        return False

def format_admin_notification(event_type, user_id, user_info, sub_info):
    """Formats the notification for the admin."""
    event_text = "✅ Новая покупка подписки" if event_type == 'purchase' else "✅ Новое продление подписки"

    return f"""
{event_text}
<blockquote>
👤 Пользователь: {user_id} (@{user_info.get('username', 'Не указан')})
📝 Тариф: {sub_info.get('tariff_name', 'N/A')}
🌐 Сервер: {sub_info.get('server_name', 'N/A')} {get_country_flag(sub_info.get('server_name', ''))}
📅 {"Куплено на" if event_type == 'purchase' else "Продлено на"}: {sub_info.get('days', 'N/A')} дней
💳 Способ оплаты: {sub_info.get('payment_method', 'N/A')}
💰 Сумма: {sub_info.get('amount', 'N/A')} руб.
🕒 Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
</blockquote>
"""

def format_user_notification(event_type, sub_info):
    """Formats the notification for the user."""
    if event_type == 'purchase':
        return f"""
🎉 Успешная оплата подписки!
<blockquote>
📅 Новая дата окончания: {sub_info.get('end_date_formatted', 'N/A')} (осталось всего {sub_info.get('days_left', 'N/A')} дней)
📦 Тарифный план: {sub_info.get('tariff_name', 'N/A')}
💳 Способ оплаты: {sub_info.get('payment_method', 'N/A')}
🌍 Сервер: {sub_info.get('server_name', 'N/A')} {get_country_flag(sub_info.get('server_name', ''))}
🔐 Данные для подключения:
<code>{sub_info.get('vless_key', 'N/A')}</code>
</blockquote>
"""
    else: # renewal
        return f"""
🎉 Успешное продление подписки!
<blockquote>
📅 Новая дата окончания: {sub_info.get('end_date_formatted', 'N/A')} (осталось всего {sub_info.get('days_left', 'N/A')} дней)
⏰ Продлено на: {sub_info.get('days', 'N/A')} дней
📦 Тарифный план: {sub_info.get('tariff_name', 'N/A')}
💳 Способ оплаты: {sub_info.get('payment_method', 'N/A')}
🌍 Сервер: {sub_info.get('server_name', 'N/A')} {get_country_flag(sub_info.get('server_name', ''))}
</blockquote>
"""

def notify_of_purchase_or_renewal(event_type, user_id, user_info, sub_info):
    """Orchestrates sending notifications for a purchase or renewal event."""
    bot_settings = DatabaseManager.get_bot_settings()
    bot_token = bot_settings.get("bot_token")
    admin_id = bot_settings.get("admin_id")

    if not bot_token:
        logger.error("Cannot send notifications: bot_token is not configured in bot_settings table.")
        return

    # Send to admin
    if admin_id:
        admin_text = format_admin_notification(event_type, user_id, user_info, sub_info)
        send_telegram_message(bot_token, admin_id, admin_text)

    # Send to user
    user_text = format_user_notification(event_type, sub_info)
    send_telegram_message(bot_token, user_id, user_text)
