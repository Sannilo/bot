"""
Модуль для определения ID пользователя Telegram Web App
"""
import json
import os

def get_user_id_from_telegram():
    """
    Получает user_id из Telegram WebApp
    Возвращает JavaScript код для получения ID пользователя
    """
    return """
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <script>
        function getTelegramUserId() {
            if (window.Telegram && window.Telegram.WebApp) {
                const user = window.Telegram.WebApp.initDataUnsafe.user;
                return user ? user.id : null;
            }
            return null;
        }

        function redirectToUserPage() {
            const userId = getTelegramUserId();
            if (userId) {
                window.location.href = "/webapp/" + userId;
            } else {
                const errorHtml = `
                <!DOCTYPE html>
                <html lang="ru">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Ошибка</title>
                    <link rel="stylesheet" href="/static/style.css">
                    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
                    <style>
                        /* Дополнительные стили для центрирования */
                        .error-container {
                            display: flex;
                            flex-direction: column;
                            justify-content: center;
                            align-items: center;
                            text-align: center;
                            height: 80vh;
                        }
                        .error-icon {
                            font-size: 48px;
                            color: var(--danger-color, #ff4444);
                            margin-bottom: 20px;
                        }
                        .error-message {
                            font-size: 20px;
                            margin-bottom: 30px;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="error-container">
                            <i class="fas fa-exclamation-triangle error-icon"></i>
                            <h2 class="error-message">Ошибка: Не удалось получить ID пользователя</h2>
                            <button class="btn btn-primary" onclick="window.location.reload()">
                                <i class="fas fa-redo"></i>
                                Попробовать снова
                            </button>
                        </div>
                    </div>
                </body>
                </html>
                `;
                document.documentElement.innerHTML = errorHtml;
            }
        }

        // Автоматическое перенаправление при загрузке
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', redirectToUserPage);
        } else {
            redirectToUserPage();
        }
    </script>
    """

def load_app_config():
    """Загружает конфигурацию приложения из app.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'static', 'app.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            return config_data[0]
    except (FileNotFoundError, json.JSONDecodeError, IndexError) as e:
        raise Exception(f"Ошибка загрузки конфигурации: {e}")

def generate_url(page_key):
    """Генерирует URL на основе конфигурации из app.json, без user_id"""
    config = load_app_config()

    # Главная страница теперь в корне
    if page_key == 'index.html':
        return "/"

    # Формируем путь для остальных страниц
    page_path = config.get(page_key)
    if page_path is None:
        # Возвращаем корневой URL, если ключ страницы не найден
        return "/"

    return f"/{config['directory']}{page_path}"
