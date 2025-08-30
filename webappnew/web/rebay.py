"""
Обработчик страницы продления подписки
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
import asyncio
import aiosqlite
import os
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from loguru import logger
import sys

# Fix for module import path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Start Adaptation for webappnew ---
from bd import DB, DatabaseManager
from yookassa import Configuration, Payment
from handlers.x_ui import xui_manager
from handlers.x_ui_ss import xui_ss_manager
from webappnew.web.notifier import notify_of_purchase_or_renewal
import threading
import time
# --- End Adaptation for webappnew ---

rebay_bp = Blueprint('rebay', __name__)

def format_subscriptions_for_display(subscriptions: list) -> list:
    result = []
    for sub in subscriptions:
        days_left = sub.get('days_left', 0)
        hours_left = sub.get('hours_left', 0)
        if days_left > 0:
            time_display = f"{days_left}д"
        elif hours_left > 0:
            time_display = f"{hours_left}ч"
        else:
            time_display = "<1ч"
        
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

        new_sub = sub.copy()
        new_sub['display_name_selected'] = f"{sub['server_name']} | {time_display} | <span class='server-id'>{key_ending}</span>"
        new_sub['display_name_option'] = f"{sub['server_name']} | {time_display} <span class='server-id'>{key_ending}</span>"
        result.append(new_sub)
    return result

class RenewalDatabase:
    """Класс для работы с базой данных при продлении подписок"""

    def __init__(self):
        self.db_path = DatabaseManager.get_db_path()

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("SELECT * FROM user WHERE telegram_id = ?", (telegram_id,)) as cursor:
                    user = await cursor.fetchone()
                    return dict(user) if user else None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None

    async def get_user_balance(self, telegram_id: int) -> float:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute('SELECT balance FROM user_balance WHERE user_id = ?', (telegram_id,)) as cursor:
                    result = await cursor.fetchone()
                    return float(result[0]) if result else 0.0
        except Exception as e:
            logger.error(f"Ошибка при получении баланса пользователя: {e}")
            return 0.0

    async def deduct_balance(self, telegram_id: int, amount: float) -> bool:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                current_balance = await self.get_user_balance(telegram_id)
                if current_balance < amount: return False
                new_balance = current_balance - amount
                await conn.execute("UPDATE user_balance SET balance = ? WHERE user_id = ?", (new_balance, telegram_id))
                await conn.execute("INSERT INTO balance_transactions (user_id, amount, type, description, status) VALUES (?, ?, 'debit', 'Продление подписки', 'succeeded')", (telegram_id, -amount))
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при списании с баланса: {e}")
            return False

    async def get_subscription_by_id(self, subscription_id: int) -> Optional[Dict]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("""
                    SELECT us.*, t.name as tariff_name, t.price, t.left_day,
                           s.name as server_name, s.protocol, s.ip, s.url, s.port,
                           s.secret_path, s.username, s.password, s.secretkey, s.inbound_id
                    FROM user_subscription us
                    INNER JOIN tariff t ON us.tariff_id = t.id
                    INNER JOIN server_settings s ON us.server_id = s.id
                    WHERE us.id = ?
                """, (subscription_id,)) as cursor:
                    subscription = await cursor.fetchone()
                    return dict(subscription) if subscription else None
        except Exception as e:
            logger.error(f"Ошибка при получении подписки по ID {subscription_id}: {e}")
            return None

    async def get_tariff_by_id(self, tariff_id: int) -> Optional[Dict]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("""
                    SELECT t.*, s.name as server_name, s.protocol, s.ip, s.url, s.port,
                           s.secret_path, s.username, s.password, s.secretkey, s.inbound_id
                    FROM tariff t
                    INNER JOIN server_settings s ON t.server_id = s.id
                    WHERE t.id = ? AND t.is_enable = 1
                """, (tariff_id,)) as cursor:
                    tariff = await cursor.fetchone()
                    return dict(tariff) if tariff else None
        except Exception as e:
            logger.error(f"Ошибка при получении тарифа: {e}")
            return None

    async def get_yookassa_settings(self) -> Optional[Dict]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("SELECT * FROM yookassa_settings WHERE is_enable = 1 LIMIT 1") as cursor:
                    settings = await cursor.fetchone()
                    return dict(settings) if settings else None
        except Exception as e:
            logger.error(f"Ошибка при получении настроек YooKassa: {e}")
            return None

    async def create_pending_yookassa_transaction(self, user_id: int, amount: float, payment_id: str, description: str):
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "INSERT INTO balance_transactions (user_id, amount, type, description, payment_id, status) VALUES (?, ?, 'deposit', ?, ?, 'pending')",
                    (user_id, amount, description, payment_id)
                )
                await conn.commit()
        except Exception as e:
            logger.error(f"Не удалось создать ожидающую транзакцию для payment_id {payment_id}: {e}")

    async def update_transaction_status(self, payment_id: str, status: str):
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("UPDATE balance_transactions SET status = ? WHERE payment_id = ?", (status, payment_id))
                await conn.commit()
        except Exception as e:
            logger.error(f"Не удалось обновить статус для payment_id {payment_id}: {e}")

    async def get_transaction_status(self, payment_id: str) -> Optional[str]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("SELECT status FROM balance_transactions WHERE payment_id = ?", (payment_id,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Не удалось получить статус для payment_id {payment_id}: {e}")
            return None
            
    async def get_subscription_details_by_payment_id(self, payment_id: str) -> Optional[Dict]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("""
                    SELECT us.end_date, s.name as server_name, t.name as tariff_name
                    FROM user_subscription us
                    JOIN tariff t ON us.tariff_id = t.id
                    JOIN server_settings s ON us.server_id = s.id
                    WHERE us.payment_id = ?
                """, (payment_id,)) as cursor:
                    result = await cursor.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Не удалось получить детали подписки для payment_id {payment_id}: {e}")
            return None


class RenewalYooKassaManager:
    """Менеджер для работы с YooKassa при продлении"""
    def __init__(self, db: RenewalDatabase):
        self.db = db

    async def create_payment(self, amount: float, description: str, user_id: str, tariff_name: str) -> Tuple[Optional[str], Optional[str]]:
        settings = await self.db.get_yookassa_settings()
        if not settings:
            logger.error("YooKassa settings are not configured")
            return None, None

        Configuration.account_id = settings['shop_id']
        Configuration.secret_key = settings['api_key']

        user = await self.db.get_user_by_telegram_id(int(user_id))
        username = user.get('username') if user else "N/A"

        payment = Payment.create({
            "amount": {"value": str(round(amount, 2)), "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": "https://t.me/your_bot"},
            "capture": True,
            "description": f"{description} для {username} (ID: {user_id})",
            "metadata": {"user_id": user_id, "tariff_name": tariff_name, "type": "renewal"}
        })
        return payment.id, payment.confirmation.confirmation_url


def _track_renewal_payment(payment_id: str, user_id: int, sub_id: int, tariff_id: int):
    """Фоновая задача для проверки статуса платежа продления YooKassa."""
    logger.info(f"Запущена фоновая проверка для платежа продления {payment_id}")
    start_time = time.time()
    while time.time() - start_time < 660: # 11 минут
        try:
            result = asyncio.run(renewal_manager.check_yookassa_renewal_status(payment_id, user_id, sub_id, tariff_id))
            if result and result.get('success'):
                logger.info(f"Платеж продления {payment_id} успешно обработан. Завершение фоновой задачи.")
                return
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче проверки платежа продления {payment_id}: {e}")
        
        time.sleep(20)

    logger.warning(f"Время ожидания платежа продления {payment_id} истекло. Фоновая задача завершена.")
    asyncio.run(renewal_manager.db.update_transaction_status(payment_id, 'failed'))


class RenewalManager:
    """Менеджер для продления подписок в веб-приложении"""
    def __init__(self):
        self.db = RenewalDatabase()
        self.yookassa = RenewalYooKassaManager(self.db)

    async def extend_subscription_in_xui(self, server_settings: Dict, vless_link: str, new_end_date: datetime) -> bool:
        try:
            client = await xui_manager.get_client(server_settings)
            if not client:
                logger.error(f"Не удалось получить клиента для сервера {server_settings['id']}")
                return False

            inbounds = client.inbound.get_list()
            client_id = vless_link.split('://')[1].split('@')[0]
            email = vless_link.split('#')[1] if '#' in vless_link else None
            logger.info(f"Поиск клиента: client_id={client_id}, email={email}")

            target_client = None
            for inbound in inbounds:
                if hasattr(inbound, 'settings') and hasattr(inbound.settings, 'clients'):
                    clients = inbound.settings.clients
                    found = next((c for c in clients if c.id == client_id), None)
                    if found:
                        target_client = found
                        logger.info(f"Клиент найден по ID {client_id} в inbound {inbound.id}")
                        break
                    if email:
                        found = next((c for c in clients if hasattr(c, 'email') and c.email == email), None)
                        if found:
                            target_client = found
                            logger.info(f"Клиент найден по email {email} в inbound {inbound.id}")
                            break
            
            if not target_client:
                logger.error(f"Клиент не найден ни по ID, ни по email на сервере {server_settings['id']}")
                return False

            new_expiry = int(new_end_date.timestamp() * 1000)
            target_client.expiry_time = new_expiry
            client.client.update(target_client.id, target_client)
            logger.info(f"Клиент {getattr(target_client, 'email', target_client.id)} успешно обновлен. Новая дата истечения: {new_end_date}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при продлении подписки в X-UI: {e}", exc_info=True)
            return False

    async def _extend_subscription_record(self, subscription_id: int, new_end_date: datetime, payment_id: str = None):
        end_date_str = new_end_date.strftime('%Y-%m-%d %H:%M:%S')
        async with aiosqlite.connect(self.db.db_path) as conn:
            if payment_id:
                await conn.execute("UPDATE user_subscription SET end_date = ?, is_active = 1, payment_id = ? WHERE id = ?", (end_date_str, payment_id, subscription_id))
            else:
                await conn.execute("UPDATE user_subscription SET end_date = ?, is_active = 1 WHERE id = ?", (end_date_str, subscription_id))
            await conn.commit()

    async def process_renewal_from_balance(self, user_id: int, sub_id: int, tariff_id: int) -> Dict:
        subscription = await self.db.get_subscription_by_id(sub_id)
        if not subscription: return {'success': False, 'error': 'Подписка не найдена'}

        tariff = await self.db.get_tariff_by_id(tariff_id)
        if not tariff: return {'success': False, 'error': 'Тариф не найден'}

        if not await self.db.deduct_balance(user_id, tariff['price']):
            return {'success': False, 'error': 'Недостаточно средств'}

        end_date_str = subscription['end_date'].split('.')[0]
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
        new_end_date = (end_date if end_date > datetime.now() else datetime.now()) + timedelta(days=tariff['left_day'])

        if await self.extend_subscription_in_xui(subscription, subscription['vless'], new_end_date):
            await self._extend_subscription_record(sub_id, new_end_date)
            user_info = await self.db.get_user_by_telegram_id(user_id)
            sub_info = {
                'tariff_name': tariff['name'], 'server_name': subscription['server_name'],
                'days': tariff['left_day'], 'payment_method': 'Баланс', 'amount': tariff['price'],
                'end_date_formatted': new_end_date.strftime('%d.%m.%Y %H:%M'),
                'days_left': (new_end_date - datetime.now()).days
            }
            notify_of_purchase_or_renewal('renewal', user_id, user_info, sub_info)
            return {'success': True, **sub_info}
        else:
            await self.db.deduct_balance(user_id, -tariff['price'])
            return {'success': False, 'error': 'Ошибка продления в X-UI'}

    async def create_yookassa_renewal_payment(self, user_id: int, sub_id: int, tariff_id: int) -> Dict:
        tariff = await self.db.get_tariff_by_id(tariff_id)
        if not tariff: return {'success': False, 'error': 'Тариф не найден'}

        description = f"Продление подписки {tariff['name']}"
        payment_id, payment_url = await self.yookassa.create_payment(tariff['price'], description, str(user_id), tariff['name'])
        
        if payment_id and payment_url:
            await self.db.create_pending_yookassa_transaction(user_id, tariff['price'], payment_id, description)
            thread = threading.Thread(target=_track_renewal_payment, args=(payment_id, user_id, sub_id, tariff_id), daemon=True)
            thread.start()
            return {'success': True, 'payment_id': payment_id, 'payment_url': payment_url}
        else:
            return {'success': False, 'error': 'Ошибка создания платежа YooKassa'}

    async def check_yookassa_renewal_status(self, payment_id: str, user_id: int, sub_id: int, tariff_id: int) -> Dict:
        current_status = await self.db.get_transaction_status(payment_id)
        if current_status == 'succeeded':
            return {'success': True, 'message': 'Платеж уже обработан'}

        settings = await self.db.get_yookassa_settings()
        if not settings: return {'success': False, 'error': 'Настройки YooKassa не найдены'}

        Configuration.account_id = settings['shop_id']
        Configuration.secret_key = settings['api_key']
        payment = Payment.find_one(payment_id)

        if payment.status == 'succeeded':
            subscription = await self.db.get_subscription_by_id(sub_id)
            if not subscription: return {'success': False, 'error': 'Подписка не найдена'}

            tariff = await self.db.get_tariff_by_id(tariff_id)
            if not tariff: return {'success': False, 'error': 'Тариф не найден'}

            end_date_str = subscription['end_date'].split('.')[0]
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
            new_end_date = (end_date if end_date > datetime.now() else datetime.now()) + timedelta(days=tariff['left_day'])

            if await self.extend_subscription_in_xui(subscription, subscription['vless'], new_end_date):
                # Сначала продлеваем подписку и связываем с payment_id
                await self._extend_subscription_record(sub_id, new_end_date, payment_id)
                
                # Затем обновляем статус транзакции
                await self.db.update_transaction_status(payment_id, 'succeeded')

                user_info = await self.db.get_user_by_telegram_id(user_id)
                sub_info = {
                    'tariff_name': tariff['name'], 'server_name': subscription['server_name'],
                    'days': tariff['left_day'], 'payment_method': 'ЮКасса', 'amount': tariff['price'],
                    'end_date_formatted': new_end_date.strftime('%d.%m.%Y %H:%M'),
                    'days_left': (new_end_date - datetime.now()).days
                }
                notify_of_purchase_or_renewal('renewal', user_id, user_info, sub_info)
                return {'success': True, **sub_info}
            else:
                return {'success': False, 'error': 'Ошибка продления в X-UI после оплаты'}
        else:
            return {'success': False, 'error': f'Статус платежа: {payment.status}'}

renewal_manager = RenewalManager()

@rebay_bp.route('/webapp/rebay')
def rebay_page():
    user_id = session.get('user_id')
    if not user_id:
        logger.warning("Access to /webapp/rebay without user_id in session.")
        return render_template('rebay.html', user_id=None, subscriptions=[], servers=[], server_tariffs={}, error="User ID not found in session.")

    subscriptions = DB.get_user_subscriptions_data(user_id)
    tariffs_data = DB.get_purchase_data()
    return render_template('rebay.html',
                         user_id=user_id,
                         subscriptions=subscriptions,
                         servers=tariffs_data.get('servers', []),
                         server_tariffs=tariffs_data.get('server_tariffs', {}))

@rebay_bp.route('/api/renewal/from_balance', methods=['POST'])
def renewal_from_balance():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    data = request.get_json()
    result = asyncio.run(renewal_manager.process_renewal_from_balance(user_id, int(data['subscription_id']), int(data['tariff_id'])))
    return jsonify(result)

@rebay_bp.route('/api/renewal/create_yookassa', methods=['POST'])
def renewal_create_yookassa():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    data = request.get_json()
    result = asyncio.run(renewal_manager.create_yookassa_renewal_payment(user_id, int(data['subscription_id']), int(data['tariff_id'])))
    return jsonify(result)

@rebay_bp.route('/api/renewal/calculate_text', methods=['POST'])
def calculate_renewal_text():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    data = request.get_json()
    subscription_id = data.get('subscription_id')
    tariff_id = data.get('tariff_id')

    if not subscription_id or not tariff_id:
        return jsonify({'success': False, 'error': 'Missing subscription_id or tariff_id'}), 400

    try:
        subscription = asyncio.run(renewal_manager.db.get_subscription_by_id(int(subscription_id)))
        tariff = asyncio.run(renewal_manager.db.get_tariff_by_id(int(tariff_id)))

        if not subscription or not tariff:
            return jsonify({'success': False, 'error': 'Subscription or tariff not found'}), 404
        
        end_date_str = subscription['end_date'].split('.')[0]
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
        time_remaining = end_date - datetime.now()
        renewal_days = tariff.get('left_day', 0)
        total_delta = time_remaining + timedelta(days=renewal_days)
        total_days = total_delta.days
        total_hours = total_delta.seconds // 3600
        
        if total_days < 0:
            total_days = 0
            total_hours = 0

        renewal_text = f"Продление: +{renewal_days} дней = {total_days} д. {total_hours} ч."
        return jsonify({'success': True, 'renewal_text': renewal_text})
    except Exception as e:
        logger.error(f"Error in calculate_renewal_text: {e}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@rebay_bp.route('/api/renewal/get_tracking_status', methods=['POST'])
def get_renewal_tracking_status():
    data = request.get_json()
    payment_id = data.get('payment_id')
    if not payment_id:
        return jsonify({'status': 'error', 'message': 'payment_id is required'}), 400

    status = asyncio.run(renewal_manager.db.get_transaction_status(payment_id))

    if status == 'succeeded':
        sub_details = asyncio.run(renewal_manager.db.get_subscription_details_by_payment_id(payment_id))
        if sub_details:
            result_data = {
                'success': True,
                'end_date_formatted': sub_details.get('end_date'),
                'server_name': sub_details.get('server_name'),
                'tariff_name': sub_details.get('tariff_name')
            }
            return jsonify({'status': 'processed', 'result': result_data})
        else:
            return jsonify({'status': 'error', 'message': 'Платеж успешен, но не удалось найти подписку'})

    elif status == 'pending':
        return jsonify({'status': 'tracking'})
    
    else: # 'failed', None, etc.
        return jsonify({'status': 'not_found'})
