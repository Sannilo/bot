"""Централизованный модуль для работы с базой данных (Синхронная версия)"""
import sqlite3
import os
from datetime import datetime, timedelta

class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    @staticmethod
    def prepare_database():
        """Проверяет и подготавливает базу данных, добавляя необходимые столбцы."""
        db_path = DatabaseManager.get_db_path()
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Проверка наличия столбца 'status' в 'balance_transactions'
            cursor.execute("PRAGMA table_info(balance_transactions)")
            columns = [info[1] for info in cursor.fetchall()]
            if 'status' not in columns:
                print("Adding 'status' column to 'balance_transactions' table.")
                # Добавляем столбец с NOT NULL и DEFAULT 'succeeded', чтобы существующие записи были валидными
                cursor.execute("ALTER TABLE balance_transactions ADD COLUMN status TEXT NOT NULL DEFAULT 'succeeded'")
                conn.commit()
                print("Column 'status' added successfully.")

            conn.close()
        except sqlite3.Error as e:
            print(f"Ошибка при подготовке базы данных: {e}")

    @staticmethod
    def get_db_path():
        """Получить путь к базе данных"""
        return os.path.join(os.path.dirname(__file__), '..', 'instance', 'database.db')

    @staticmethod
    def _execute(query, params=(), fetchone=False, fetchall=False, commit=False):
        """Универсальный метод для выполнения SQL-запросов"""
        db_path = DatabaseManager.get_db_path()
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)

            if commit:
                conn.commit()
                return cursor.lastrowid

            if fetchone:
                return cursor.fetchone()
            
            if fetchall:
                return cursor.fetchall()
            
            return None
        except sqlite3.Error as e:
            print(f"Ошибка базы данных: {e}")
            return None if fetchone or fetchall else False
        finally:
            if conn:
                conn.close()

    @staticmethod
    def get_bot_settings():
        """Получить настройки бота из базы данных"""
        query = "SELECT bot_token, admin_id FROM bot_settings WHERE is_enable = 1 LIMIT 1"
        result = DatabaseManager._execute(query, fetchone=True)
        return dict(result) if result else {}

    @staticmethod
    def get_active_servers_and_tariffs():
        query_servers = "SELECT DISTINCT s.id, s.name FROM server_settings s JOIN tariff t ON s.id = t.server_id WHERE s.is_enable = 1 AND t.is_enable = 1 ORDER BY s.name"
        servers = DatabaseManager._execute(query_servers, fetchall=True)
        query_tariffs = "SELECT t.*, s.name as server_name FROM tariff t JOIN server_settings s ON t.server_id = s.id WHERE s.is_enable = 1 AND t.is_enable = 1 ORDER BY t.server_id, t.left_day"
        tariffs = DatabaseManager._execute(query_tariffs, fetchall=True)
        if servers is None or tariffs is None: return {'servers': [], 'server_tariffs': {}}
        server_tariffs = {}
        for server in servers:
            server_id = str(server['id'])
            server_tariffs[server_id] = []
            base_30day = next((t for t in tariffs if str(t['server_id']) == server_id and t['left_day'] == 30), None)
            for tariff in tariffs:
                if str(tariff['server_id']) == server_id:
                    tariff_data = {'id': tariff['id'], 'name': tariff['name'], 'price': tariff['price'], 'days': tariff['left_day'], 'description': tariff['description'] or '', 'is_popular': 28 <= tariff['left_day'] <= 32, 'savings_percent': 0}
                    if base_30day and tariff['left_day'] > 30:
                        expected_price = (tariff['left_day'] / 30) * base_30day['price']
                        if expected_price > 0:
                            savings = max(0, int(((expected_price - tariff['price']) / expected_price) * 100))
                            tariff_data['savings_percent'] = savings
                    server_tariffs[server_id].append(tariff_data)
        return {'servers': [{'id': s['id'], 'name': s['name']} for s in servers], 'server_tariffs': server_tariffs}

    @staticmethod
    def get_user_by_telegram_id(user_id):
        return DatabaseManager._execute("SELECT * FROM user WHERE telegram_id = ?", (user_id,), fetchone=True)

    @staticmethod
    def get_user_balance(user_id):
        result = DatabaseManager._execute("SELECT balance FROM user_balance WHERE user_id = ?", (user_id,), fetchone=True)
        return float(result['balance']) if result else 0.0

    @staticmethod
    def get_active_subscriptions_count(user_id):
        result = DatabaseManager._execute("SELECT COUNT(*) as total_keys FROM user_subscription WHERE user_id = ? AND is_active = 1", (user_id,), fetchone=True)
        return result['total_keys'] if result else 0

    @staticmethod
    def get_user_subscriptions(user_id):
        return DatabaseManager._execute("SELECT us.*, s.name as server_name, t.name as tariff_name FROM user_subscription us LEFT JOIN server_settings s ON us.server_id = s.id LEFT JOIN tariff t ON us.tariff_id = t.id WHERE us.user_id = ? AND us.is_active = 1 ORDER BY us.end_date DESC", (user_id,), fetchall=True)

    @staticmethod
    def get_latest_user_subscription(user_id):
        return DatabaseManager._execute("SELECT us.*, s.name as server_name FROM user_subscription us JOIN server_settings s ON us.server_id = s.id WHERE us.user_id = ? ORDER BY us.is_active DESC, us.end_date DESC LIMIT 1", (user_id,), fetchone=True)

    @staticmethod
    def get_full_subscription_for_replacement(subscription_id, user_id):
        query = "SELECT us.*, ss.*, t.id as tariff_id, t.name as tariff_name, us.user_id as telegram_id FROM user_subscription us JOIN server_settings ss ON us.server_id = ss.id JOIN tariff t ON us.tariff_id = t.id WHERE us.id = ? AND us.is_active = 1 AND us.user_id = ?"
        return DatabaseManager._execute(query, (subscription_id, user_id), fetchone=True)
        
    @staticmethod
    def get_server_settings(server_id):
        return DatabaseManager._execute("SELECT * FROM server_settings WHERE id = ? AND is_enable = 1", (server_id,), fetchone=True)

    @staticmethod
    def deactivate_subscription(subscription_id):
        return DatabaseManager._execute("UPDATE user_subscription SET is_active = 0 WHERE id = ?", (subscription_id,), commit=True)

    @staticmethod
    def create_replaced_subscription(user_id, tariff_id, new_server_id, end_date, new_key, payment_id):
        query = "INSERT INTO user_subscription (user_id, tariff_id, server_id, end_date, vless, is_active, payment_id) VALUES (?, ?, ?, ?, ?, 1, ?)"
        params = (user_id, tariff_id, new_server_id, end_date, new_key, payment_id)
        return DatabaseManager._execute(query, params, commit=True)

    @staticmethod
    def format_date(date_str):
        if not date_str: return None, 'Неизвестно', 0
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d.%m.%Y']:
            try:
                reg_date = datetime.strptime(date_str, fmt)
                days_since_reg = (datetime.now() - reg_date).days
                return reg_date, reg_date.strftime('%d.%m.%Y'), days_since_reg
            except (ValueError, TypeError): continue
        return None, date_str, 0

    @staticmethod
    def calculate_subscription_time(start_date_str, end_date_str):
        try:
            start_date = datetime.strptime(start_date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            end_date = datetime.strptime(end_date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            if end_date < now: return {'status': 'expired', 'days_left': 0, 'hours_left': 0, 'minutes_left': 0, 'seconds_left': 0, 'time_display': "0с", 'formatted_date': end_date.strftime('%d.%m.%Y'), 'progress_percent': 100}
            total_seconds = (end_date - start_date).total_seconds()
            progress_percent = int(((now - start_date).total_seconds() / total_seconds) * 100) if total_seconds > 0 else 0
            remaining = (end_date - now).total_seconds()
            days, rem = divmod(remaining, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)
            if days > 0: time_display = f"{int(days)}д"
            elif hours > 0: time_display = f"{int(hours)}ч"
            else: time_display = f"{int(minutes)}м"
            return {'status': 'active', 'days_left': int(days), 'hours_left': int(hours), 'minutes_left': int(minutes), 'seconds_left': int(seconds), 'time_display': time_display, 'formatted_date': end_date.strftime('%d.%m.%Y'), 'progress_percent': progress_percent}
        except (ValueError, TypeError): return {'status': 'error', 'days_left': 0, 'hours_left': 0, 'minutes_left': 0, 'seconds_left': 0, 'time_display': "0с", 'formatted_date': 'Ошибка', 'progress_percent': 0}

class DB:
    @staticmethod
    def get_user_profile_data(user_id):
        user = DatabaseManager.get_user_by_telegram_id(user_id)
        if not user: return {'balance': 0.0, 'registration_date': 'Неизвестно', 'days_since_registration': 0, 'total_keys': 0}
        balance = DatabaseManager.get_user_balance(user_id)
        total_keys = DatabaseManager.get_active_subscriptions_count(user_id)
        _, formatted_reg_date, days_since_reg = DatabaseManager.format_date(user['date'])
        return {'balance': balance, 'registration_date': formatted_reg_date, 'days_since_registration': days_since_reg, 'total_keys': total_keys}

    @staticmethod
    def get_user_subscriptions_data(user_id):
        subscriptions = DatabaseManager.get_user_subscriptions(user_id)
        if not subscriptions: return []
        result = []
        for sub in subscriptions:
            time_data = DatabaseManager.calculate_subscription_time(sub['start_date'], sub['end_date'])
            if time_data['status'] != 'expired':
                result.append({
                    'id': sub['id'],
                    'server_id': sub['server_id'] or 1,
                'server_name': sub['server_name'] or 'Неизвестно',
                'tariff_name': sub['tariff_name'] or 'Неизвестно',
                'vless': sub['vless'] or '',
                'is_active': True,
                **time_data
            })
        return result

    @staticmethod
    def get_user_subscription_data(user_id):
        subscription = DatabaseManager.get_latest_user_subscription(user_id)
        if not subscription: return {'status': 'no_subscription', 'expiry_date': None, 'days_left': 0, 'hours_left': 0, 'time_display': "0ч", 'server_name': None, 'progress_percent': 0}
        time_data = DatabaseManager.calculate_subscription_time(subscription['start_date'], subscription['end_date'])
        return {'status': time_data['status'], 'expiry_date': time_data['formatted_date'], 'days_left': time_data['days_left'], 'hours_left': time_data['hours_left'], 'time_display': time_data['time_display'], 'progress_percent': time_data['progress_percent'], 'server_name': subscription['server_name']}

    @staticmethod
    def get_user_balance(user_id):
        return DatabaseManager.get_user_balance(user_id)

    @staticmethod
    def get_purchase_data():
        return DatabaseManager.get_active_servers_and_tariffs()
