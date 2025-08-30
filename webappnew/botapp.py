"""
Главный файл для запуска Telegram Web App
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
import sys
import asyncio
from functools import wraps
from dotenv import load_dotenv
from core import load_app_config, generate_url, get_user_id_from_telegram
from web.rebay import format_subscriptions_for_display

# Загружаем переменные окружения из .env файла
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

# Добавляем путь для импорта модулей
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Импортируем функции для работы с базой данных
from bd import DatabaseManager, DB

# Подготовка базы данных (например, добавление новых столбцов)
DatabaseManager.prepare_database()

# Импортируем blueprint
from web.rebay import rebay_bp
from web.by import by_bp


app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = os.getenv("SECRET_KEY", "a-default-safe-secret-key")

# Регистрируем blueprints
app.register_blueprint(rebay_bp)
app.register_blueprint(by_bp)

# Загружаем конфигурацию
APP_CONFIG = load_app_config()

# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('webapp_redirect'))
        return f(*args, **kwargs)
    return decorated_function

# Добавляем функции в контекст шаблонов
@app.context_processor
def inject_config():
    return {'app_config': APP_CONFIG, 'generate_url': generate_url}

# --- Маршруты ---

@app.route('/ad/pro')
def admin_login():
    """Безопасный вход для админа для просмотра профиля пользователя."""
    admin_key = request.args.get('key')
    target_user_id = request.args.get('id')
    expected_admin_key = os.getenv("ADMIN_KEY_PRO")

    if not all([admin_key, target_user_id, expected_admin_key]):
        return "Ошибка: Отсутствуют параметры.", 400

    if admin_key != expected_admin_key:
        return "Ошибка: Неверный ключ админа.", 403

    try:
        session['user_id'] = int(target_user_id)
        session['is_admin_view'] = True
        return redirect(url_for('index'))
    except (ValueError, TypeError):
        return "Ошибка: Неверный ID пользователя.", 400

@app.route('/webapp')
def webapp_redirect():
    """Автоматически определяет user_id из Telegram WebApp"""
    return f"""
    <!DOCTYPE html><html><head><title>VPN WebApp</title><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
    <body><h2>Загрузка...</h2>{get_user_id_from_telegram()}</body></html>
    """

@app.route('/webapp/<int:user_id>')
def webapp_user_redirect(user_id):
    """Сохраняет user_id в сессию и перенаправляет на главную страницу"""
    session['user_id'] = user_id
    return redirect(url_for('index'))

@app.route("/")
@login_required
def index():
    user_id = session['user_id']
    subscription = DB.get_user_subscription_data(user_id)
    return render_template('index.html', user_id=user_id, subscription=subscription)

@app.route(f"/{APP_CONFIG['directory']}{APP_CONFIG['profile.html']}")
@login_required
def profile():
    return render_template('profile.html', user_id=session['user_id'])

@app.route(f"/{APP_CONFIG['directory']}{APP_CONFIG['purchase.html']}")
@login_required
def purchase():
    servers_and_tariffs = DatabaseManager.get_active_servers_and_tariffs()
    return render_template('by.html', user_id=session['user_id'], **servers_and_tariffs)

@app.route(f"/{APP_CONFIG['directory']}{APP_CONFIG['renewal.html']}")
@login_required
def renewal():
    from web.rebay import RebayHandler
    return RebayHandler.handle(session['user_id'])

@app.route(f"/{APP_CONFIG['directory']}{APP_CONFIG['replace.html']}")
@login_required
def replace():
    return render_template('rekey.html', user_id=session['user_id'])

@app.route(f"/{APP_CONFIG['directory']}{APP_CONFIG['installapp.html']}")
@login_required
def installapp():
    from web.appinstall import AppHandler
    return AppHandler.handle(session['user_id'])

@app.route(f"/{APP_CONFIG['directory']}{APP_CONFIG['support.html']}")
@login_required
def support():
    return render_template('support.html', user_id=session['user_id'])

# --- API ---

@app.route('/api/user-profile')
@login_required
def user_profile_api():
    profile_data = DB.get_user_profile_data(session['user_id'])
    return jsonify({'profile': profile_data})

@app.route('/api/user-subscriptions')
@login_required
def user_subscriptions_api():
    subscriptions_data = DB.get_user_subscriptions_data(session['user_id'])
    formatted_subscriptions = format_subscriptions_for_display(subscriptions_data)
    return jsonify({'subscriptions': formatted_subscriptions})

@app.route('/api/user-balance')
@login_required
def user_balance_api():
    balance = DB.get_user_balance(session['user_id'])
    return jsonify({"balance": balance})

@app.route('/api/replace/user-keys')
@login_required
def get_user_keys_api():
    from web.rekey import get_user_keys
    keys = get_user_keys(session['user_id'])
    return jsonify({'success': True, 'keys': keys})

@app.route('/api/replace/available-servers/<int:current_server_id>/<protocol>')
def get_available_servers_api(current_server_id, protocol):
    from web.rekey import get_available_servers
    servers = get_available_servers(current_server_id, protocol)
    return jsonify({'success': True, 'servers': servers})

@app.route('/api/replace/execute', methods=['POST'])
@login_required
def execute_key_replacement_api():
    user_id = session['user_id']
    data = request.get_json()
    old_key_id = data.get('old_key_id')
    new_server_id = data.get('new_server_id')
    if not all([old_key_id, new_server_id]):
        return jsonify({'success': False, 'error': 'Отсутствуют обязательные параметры'})

    from web.rekey import replace_key
    result = replace_key(user_id, old_key_id, new_server_id)
    return jsonify(result)

if __name__ == '__main__':
    port = int(APP_CONFIG.get('port', 5000))
    debug_mode = os.getenv("FLASK_DEBUG") == "True"
    
    # Путь к SSL сертификатам
    cert_path = '/etc/letsencrypt/live/one.tgone.ru/fullchain.pem'
    key_path = '/etc/letsencrypt/live/one.tgone.ru/privkey.pem'

    ssl_context = None
    if os.path.exists(cert_path) and os.path.exists(key_path):
        ssl_context = (cert_path, key_path)
        
    app.run(host='0.0.0.0', port=port, debug=debug_mode, ssl_context=ssl_context)
