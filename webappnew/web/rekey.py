import os
from datetime import datetime
from typing import Dict, List
from loguru import logger
import sys
import re
import asyncio

from bd import DB, DatabaseManager

try:
    from handlers.x_ui import xui_manager
    from handlers.x_ui_ss import xui_ss_manager
    import py3xui
except ImportError:
    logger.warning("XUI managers not found")
    xui_manager = None
    xui_ss_manager = None
    py3xui = None

def get_user_keys(telegram_id: int) -> List[Dict]:
    """Get a list of active user keys using the centralized DB class."""
    try:
        subscriptions = DB.get_user_subscriptions_data(telegram_id)
        result = []
        for sub in subscriptions:
            protocol = 'shadowsocks' if sub.get('vless', '').startswith('ss://') else 'vless'
            key_ending = ""
            vless_link = sub.get('vless', '')
            if '#' in vless_link:
                key_name = vless_link.split('#')[-1]
                if 'tg_' in key_name:
                    try:
                        key_ending = "@" + key_name.split('@')[-1]
                    except:
                        key_ending = "@..." + key_name[-6:]
                else:
                    key_ending = "@..." + key_name[-6:]
            elif '@' in vless_link:
                host_part = vless_link.split('@')[-1].split('?')[0]
                key_ending = "@..." + host_part[-10:]
            
            days_left = sub.get('days_left', 0)
            hours_left = sub.get('hours_left', 0)
            if days_left > 0:
                time_display = f"{days_left}д"
            elif hours_left > 0:
                time_display = f"{hours_left}ч"
            else:
                time_display = "<1ч"
            
            result.append({
                'id': sub['id'],
                'server_name': sub['server_name'],
                'tariff_name': sub['tariff_name'],
                'end_date': sub.get('formatted_date', ''),
                'days_left': sub.get('days_left', 0),
                'hours_left': sub.get('hours_left', 0),
                'protocol': protocol,
                'server_id': sub['server_id'],
                'vless': sub['vless'],
                'key_ending': key_ending,
                'display_name_selected': f"{sub['server_name']} | {time_display} | <span class='server-id'>{key_ending}</span>",
                'display_name_option': f"{sub['server_name']} | {time_display} <span class='server-id'>{key_ending}</span>",
                'replace_display': f"{sub['server_name']} - {key_ending}"
            })
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении ключей пользователя: {e}")
        return []

def get_available_servers(current_server_id: int, protocol: str) -> List[Dict]:
    """Get a list of available servers for replacement using the centralized DB class."""
    try:
        all_servers_data = DatabaseManager.get_active_servers_and_tariffs()
        all_servers = all_servers_data.get('servers', [])
        
        result = []
        for server in all_servers:
            if server['id'] != current_server_id:
                 result.append({
                     'id': server['id'],
                     'name': server['name'],
                     'protocol': protocol,
                     'available': True
                 })
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении доступных серверов: {e}")
        return []

def replace_key(telegram_id: int, old_key_id: int, new_server_id: int) -> Dict:
    """Replace a key with a new server, now using centralized DB calls."""
    import asyncio
    try:
        old_subscription = DatabaseManager.get_full_subscription_for_replacement(old_key_id, telegram_id)
        if not old_subscription:
            return {'success': False, 'error': 'Подписка не найдена или неактивна'}

        new_server = DatabaseManager.get_server_settings(new_server_id)
        if not new_server:
            return {'success': False, 'error': 'Новый сервер недоступен'}

        is_shadowsocks = old_subscription['vless'].startswith('ss://')
        end_date = old_subscription['end_date'].split('.')[0]
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        days_left = max(1, int((end_datetime - datetime.now()).total_seconds() / 86400))
        
        server_settings = dict(new_server)
        trial_settings = {'left_day': days_left}

        if is_shadowsocks:
            if not xui_ss_manager: return {'success': False, 'error': 'XUI SS Manager не найден'}
            new_key = asyncio.run(xui_ss_manager.create_ss_user(server_settings=server_settings, trial_settings=trial_settings, telegram_id=old_subscription['telegram_id']))
        else:
            if not xui_manager: return {'success': False, 'error': 'XUI Manager не найден'}
            new_key = asyncio.run(xui_manager.create_trial_user(server_settings=server_settings, trial_settings=trial_settings, telegram_id=old_subscription['telegram_id']))

        if not new_key:
            return {'success': False, 'error': 'Ошибка при создании нового ключа'}

        try:
            if is_shadowsocks:
                asyncio.run(xui_ss_manager.delete_ss_user(server_settings=dict(old_subscription), email=f"tg_{old_subscription['telegram_id']}@"))
            else:
                uuid_match = re.search(r'vless://([^@]+)@', old_subscription['vless'])
                if uuid_match:
                    client_uuid = uuid_match.group(1)
                    api_url = f"{old_subscription['url']}:{old_subscription['port']}/{old_subscription['secret_path']}"
                    async def delete_client():
                        api = py3xui.AsyncApi(host=api_url, username=old_subscription['username'], password=old_subscription['password'], use_tls_verify=False)
                        await api.login()
                        await api.client.delete(old_subscription['inbound_id'], client_uuid)
                    asyncio.run(delete_client())
                    logger.info(f"Клиент успешно удален с сервера {api_url}")
        except Exception as e:
            logger.warning(f"Не удалось удалить старый ключ: {e}")

        DatabaseManager.deactivate_subscription(old_key_id)
        DatabaseManager.create_replaced_subscription(
            user_id=old_subscription['telegram_id'],
            tariff_id=old_subscription['tariff_id'],
            new_server_id=new_server_id,
            end_date=end_date,
            new_key=new_key,
            payment_id=old_subscription['payment_id']
        )

        return {'success': True, 'new_key': new_key, 'server_name': new_server['name'], 'tariff_name': old_subscription['tariff_name'], 'end_date': end_date}

    except Exception as e:
        logger.error(f"Ошибка при замене ключа: {e}")
        return {'success': False, 'error': str(e)}
