"""
Обработчик страницы покупки подписки
"""
from flask import Blueprint, render_template, request, jsonify, session
import asyncio
import aiosqlite
import os
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from loguru import logger
import threading
import time
import uuid
import sys

# Fix for module import path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from bd import DB, DatabaseManager
from yookassa import Configuration, Payment
from handlers.x_ui import xui_manager
from webappnew.web.notifier import notify_of_purchase_or_renewal

by_bp = Blueprint('by', __name__)

class PurchaseDatabase:
    """Класс для работы с базой данных при покупке"""
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

    async def get_user_balance(self, telegram_id: int) -> float:
        """Получить баланс пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute('SELECT balance FROM user_balance WHERE user_id = ?', (telegram_id,)) as cursor:
                    result = await cursor.fetchone()
                    return float(result[0]) if result else 0.0
        except Exception as e:
            logger.error(f"Ошибка при получении баланса пользователя: {e}")
            return 0.0

    async def deduct_balance(self, telegram_id: int, amount: float, reason: str) -> bool:
        """Списать средства с баланса пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("UPDATE user_balance SET balance = balance - ? WHERE user_id = ?", (amount, telegram_id))
                await conn.execute("INSERT INTO balance_transactions (user_id, amount, type, description) VALUES (?, ?, 'debit', ?)", (telegram_id, -amount, reason))
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при списании с баланса: {e}")
            return False

    async def create_pending_yookassa_transaction(self, user_id: int, amount: float, payment_id: str, description: str):
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO balance_transactions (user_id, amount, type, description, payment_id, status)
                    VALUES (?, ?, 'deposit', ?, ?, 'pending')
                    """,
                    (user_id, amount, description, payment_id)
                )
                await conn.commit()
        except Exception as e:
            logger.error(f"Не удалось создать ожидающую транзакцию для payment_id {payment_id}: {e}")

    async def update_transaction_status(self, payment_id: str, status: str):
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "UPDATE balance_transactions SET status = ? WHERE payment_id = ?",
                    (status, payment_id)
                )
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
                    SELECT us.vless, us.end_date, t.name as tariff_name, s.name as server_name, t.left_day
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

class PurchaseYooKassaManager:
    """Менеджер для работы с YooKassa при покупке"""
    def __init__(self, db: PurchaseDatabase):
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
            "metadata": {"user_id": user_id, "tariff_name": tariff_name, "type": "purchase"}
        })
        return payment.id, payment.confirmation.confirmation_url

def _track_payment(payment_id: str, user_id: int, tariff_id: int):
    """Фоновая задача для проверки статуса платежа YooKassa."""
    logger.info(f"Запущена фоновая проверка для платежа покупки {payment_id}")
    start_time = time.time()
    while time.time() - start_time < 660: # 11 минут
        try:
            # Запускаем асинхронную проверку в новом цикле событий
            result = asyncio.run(purchase_manager.check_yookassa_purchase_status(payment_id, user_id, tariff_id))
            # Если платеж успешно обработан, выходим из цикла
            if result and result.get('success'):
                logger.info(f"Платеж покупки {payment_id} успешно обработан. Завершение фоновой задачи.")
                return
        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче проверки платежа {payment_id}: {e}")
        
        time.sleep(20) # Пауза между проверками

    logger.warning(f"Время ожидания платежа {payment_id} истекло. Фоновая задача завершена.")
    # Опционально: обновить статус в БД на 'expired' или 'failed'
    asyncio.run(purchase_manager.db.update_transaction_status(payment_id, 'failed'))


class PurchaseManager:
    """Менеджер для покупки подписок"""
    def __init__(self):
        self.db = PurchaseDatabase()
        self.yookassa = PurchaseYooKassaManager(self.db)

    async def _create_xui_key(self, tariff_data, user_id):
        if not xui_manager: return f"vless://mock-key-{user_id}"
        return await xui_manager.create_trial_user(server_settings=tariff_data, trial_settings=tariff_data, telegram_id=user_id)

    async def _create_subscription(self, user_id: int, tariff_data: Dict, payment_method: str, payment_id: str = None) -> Dict:
        try:
            end_date = datetime.now() + timedelta(days=tariff_data['left_day'])
            vless_key = await self._create_xui_key(tariff_data, user_id)
            if not vless_key: return {'success': False, 'error': 'Ошибка при создании ключа в 3x-ui'}

            async with aiosqlite.connect(self.db.db_path) as conn:
                await conn.execute(
                    "INSERT INTO user_subscription (user_id, tariff_id, server_id, end_date, vless, is_active, start_date, payment_id) VALUES (?, ?, ?, ?, ?, 1, ?, ?)",
                    (user_id, tariff_data['id'], tariff_data['server_id'], end_date.strftime('%Y-%m-%d %H:%M:%S'), vless_key, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), payment_id)
                )
                await conn.commit()

            user_info = await self.db.get_user_by_telegram_id(user_id)
            sub_info = {
                'tariff_name': tariff_data['name'], 'server_name': tariff_data['server_name'],
                'days': tariff_data['left_day'], 'payment_method': payment_method,
                'amount': tariff_data['price'], 'end_date_formatted': end_date.strftime('%d.%m.%Y'),
                'days_left': tariff_data['left_day'], 'vless_key': vless_key
            }
            notify_of_purchase_or_renewal('purchase', user_id, user_info, sub_info)

            return {'success': True, **sub_info}
        except Exception as e:
            logger.error(f"Ошибка при создании подписки: {e}", exc_info=True)
            return {'success': False, 'error': 'Ошибка при создании подписки'}

    async def create_yookassa_purchase_payment(self, user_id: int, tariff_id: int) -> Dict:
        tariff = await self.db.get_tariff_by_id(tariff_id)
        if not tariff: return {'success': False, 'error': 'Тариф не найден'}

        description = f"Покупка подписки {tariff['name']}"
        payment_id, payment_url = await self.yookassa.create_payment(tariff['price'], description, str(user_id), tariff['name'])

        if payment_id and payment_url:
            # Создаем запись в БД со статусом 'pending'
            await self.db.create_pending_yookassa_transaction(user_id, tariff['price'], payment_id, description)
            
            # Запускаем фоновую задачу для отслеживания
            thread = threading.Thread(target=_track_payment, args=(payment_id, user_id, tariff_id), daemon=True)
            thread.start()
            
            return {'success': True, 'payment_id': payment_id, 'payment_url': payment_url}
        else:
            return {'success': False, 'error': 'Ошибка создания платежа YooKassa'}

    async def _deduct_balance(self, user_id: int, amount: float, reason: str) -> bool:
        current_balance = await self.db.get_user_balance(user_id)
        if current_balance < amount:
            return False
        return await self.db.deduct_balance(user_id, amount, reason)

    async def process_purchase_from_balance(self, user_id: int, tariff_id: int) -> Dict:
        tariff_data = await self.db.get_tariff_by_id(tariff_id)
        if not tariff_data:
            return {'success': False, 'error': 'Тариф не найден'}

        if not await self._deduct_balance(user_id, tariff_data['price'], f"Покупка подписки {tariff_data['name']}"):
            return {'success': False, 'error': 'Недостаточно средств на балансе'}

        return await self._create_subscription(user_id, tariff_data, 'Баланс')

    async def check_yookassa_purchase_status(self, payment_id: str, user_id: int, tariff_id: int) -> Dict:
        # Проверяем, не был ли платеж уже обработан
        current_status = await self.db.get_transaction_status(payment_id)
        if current_status == 'succeeded':
            return {'success': True, 'message': 'Платеж уже обработан'}

        settings = await self.db.get_yookassa_settings()
        if not settings: return {'success': False, 'error': 'Настройки YooKassa не найдены'}

        Configuration.account_id = settings['shop_id']
        Configuration.secret_key = settings['api_key']
        payment = Payment.find_one(payment_id)

        if payment.status == 'succeeded':
            tariff_data = await self.db.get_tariff_by_id(tariff_id)
            if not tariff_data: return {'success': False, 'error': 'Тариф не найден'}
            
            # Сначала создаем подписку и связываем ее с payment_id
            result = await self._create_subscription(user_id, tariff_data, 'ЮКасса', payment_id=payment_id)
            
            # И только потом обновляем статус транзакции. Это решает race condition.
            if result.get('success'):
                await self.db.update_transaction_status(payment_id, 'succeeded')
            
            return result
        else:
            return {'success': False, 'error': f'Статус платежа: {payment.status}'}


purchase_manager = PurchaseManager()

# --- API Endpoints ---
@by_bp.route('/webapp/by')
def by_page():
    user_id = session.get('user_id') or request.args.get('user_id')
    if user_id:
        session['user_id'] = user_id
    if not user_id:
        return "User ID not found.", 400

    tariffs_data = DB.get_purchase_data()
    return render_template('by.html',
                         user_id=user_id,
                         servers=tariffs_data.get('servers', []),
                         server_tariffs=tariffs_data.get('server_tariffs', {}))

@by_bp.route('/api/purchase/create_yookassa', methods=['POST'])
def purchase_create_yookassa():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    data = request.get_json()
    result = asyncio.run(purchase_manager.create_yookassa_purchase_payment(user_id, int(data['tariff_id'])))
    return jsonify(result)

@by_bp.route('/api/purchase/from_balance', methods=['POST'])
def purchase_from_balance():
    user_id = session.get('user_id')
    if not user_id: return jsonify({'success': False, 'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    tariff_id = data.get('tariff_id')
    if not tariff_id:
        return jsonify({'success': False, 'error': 'Tariff ID is required'}), 400
    
    result = asyncio.run(purchase_manager.process_purchase_from_balance(user_id, int(tariff_id)))
    return jsonify(result)

@by_bp.route('/api/purchase/get_tracking_status', methods=['POST'])
def get_purchase_tracking_status():
    data = request.get_json()
    payment_id = data.get('payment_id')
    if not payment_id:
        return jsonify({'status': 'error', 'message': 'payment_id is required'}), 400

    # Получаем статус напрямую из БД
    status = asyncio.run(purchase_manager.db.get_transaction_status(payment_id))

    if status == 'succeeded':
        # Если успешно, получаем детали подписки для отображения в модальном окне
        sub_details = asyncio.run(purchase_manager.db.get_subscription_details_by_payment_id(payment_id))
        if sub_details:
            # Формируем ответ, который ожидает фронтенд
            result_data = {
                'success': True,
                'vless_key': sub_details.get('vless'),
                'end_date_formatted': sub_details.get('end_date'), # Можно добавить форматирование
                'tariff_name': sub_details.get('tariff_name'),
                'server_name': sub_details.get('server_name'),
                'days_left': sub_details.get('left_day')
            }
            return jsonify({'status': 'processed', 'result': result_data})
        else:
            # Этого не должно произойти, но на всякий случай
            return jsonify({'status': 'error', 'message': 'Платеж успешен, но не удалось найти подписку'})

    elif status == 'pending':
        return jsonify({'status': 'tracking'})
    
    else: # 'failed', None, или любая другая ошибка
        return jsonify({'status': 'not_found'})
