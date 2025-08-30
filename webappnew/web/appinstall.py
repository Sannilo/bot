"""Обработчик страницы установки приложения"""
from flask import render_template
import urllib.parse

class AppHandler:
    @staticmethod
    def handle(user_id):
        """Обработка страницы установки приложения"""
        from bd import DB

        # Получаем данные пользователя
        subscriptions = DB.get_user_subscriptions_data(user_id)

        # Формируем данные для установки
        install_data = {
            'has_subscription': False,
            'vless_link': None,
            'user_keys': [],
            'apps': AppHandler.get_app_list()
        }

        if subscriptions:
            # Получаем активные подписки
            active_subs = [sub for sub in subscriptions if sub.get('is_active')]

            if active_subs:
                install_data['has_subscription'] = True
                install_data['vless_link'] = active_subs[0].get('vless')

                # Формируем список ключей пользователя
                user_keys = []
                for sub in active_subs:
                    if sub.get('vless'):
                        server_name = sub.get('server_name', '')
                        user_keys.append({
                            'vless': sub['vless'],
                            'server_name': server_name,
                            'server_flag': '',  # Emojis removed
                            'days_left': sub.get('days_left', 0),
                            'hours_left': sub.get('hours_left', 0),
                            'key_ending': sub['vless'][-5:] if len(sub['vless']) > 5 else sub['vless']
                        })

                install_data['user_keys'] = user_keys
                install_data['apps'] = AppHandler.get_app_list(install_data['vless_link'])

        return render_template('appinstall.html', user_id=user_id, install_data=install_data)

    @staticmethod
    def get_app_list(vless_link=None):
        """Получение списка приложений с ссылками"""
        encoded_vless = urllib.parse.quote(vless_link) if vless_link else None

        apps = [
            {
                'name': 'iPhone / iPad',
                'icon': 'fab fa-apple',
                'download_url': 'https://apps.apple.com/us/app/v2raytun/id6476628951',
                'connect_url': f'https://auto.syslab.space/v2raytun?vless={encoded_vless}' if encoded_vless else None,
                'instructions': [
                    'Скачайте приложение V2rayTUN из App Store',
                    'Откройте приложение и нажмите "+" для добавления конфигурации',
                    'Вставьте ваш ключ доступа или используйте кнопку "Подключить"',
                    'Нажмите "Подключить" для активации VPN'
                ]
            },
            {
                'name': 'Android',
                'icon': 'fab fa-android',
                'download_url': 'https://play.google.com/store/search?q=v2rayTun&c=apps&hl=en_GB',
                'connect_url': f'https://auto.syslab.space/v2raytun?vless={encoded_vless}' if encoded_vless else None,
                'instructions': [
                    'Скачайте приложение V2rayTUN из Google Play',
                    'Откройте приложение и нажмите "+" для добавления сервера',
                    'Вставьте ваш ключ доступа или используйте кнопку "Подключить"',
                    'Нажмите "Подключить" для активации VPN'
                ]
            },
            {
                'name': 'Android TV',
                'icon': 'fas fa-tv',
                'download_url': 'https://play.google.com/store/search?q=v2rayTun&c=apps&hl=en_GB',
                'connect_url': f'https://auto.syslab.space/v2raytun?vless={encoded_vless}' if encoded_vless else None,
                'instructions': [
                    'Установите приложение V2rayTUN на Android TV',
                    'Откройте приложение с помощью пульта',
                    'Добавьте новую конфигурацию через "+"',
                    'Введите ваш ключ доступа и подключитесь'
                ]
            },
            {
                'name': 'Windows',
                'icon': 'fab fa-windows',
                'download_url': 'https://github.com/hiddify/hiddify-next/releases/latest/download/Hiddify-Windows-Setup-x64.exe',
                'connect_url': f'https://auto.syslab.space/hiddify?vless={vless_link}' if vless_link else None,
                'instructions': [
                    'Скачайте и установите Hiddify для Windows',
                    'Запустите приложение от имени администратора',
                    'Нажмите "+" для добавления нового профиля',
                    'Вставьте ваш ключ доступа и сохраните конфигурацию',
                    'Нажмите "Подключить" для активации VPN'
                ]
            }
        ]

        return apps
