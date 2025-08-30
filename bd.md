📋 Существующие таблицы в базе данных:
==================================================  

🔹 Таблица: bot_settings
   Столбцы:
     - bot_token: TEXT NOT NULL
     - admin_id: TEXT NOT NULL
     - chat_id: TEXT
     - chanel_id: TEXT
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
     - reg_notify: INTEGER DEFAULT 0
     - pay_notify: INTEGER DEFAULT 0
   📊 Количество записей: 1
   📝 Примеры записей:
     1. ('7580464478:AAHWNEbxhhuNs5NHn-iwPqgLdzGWwLAy2Lg', '690989250', 'None', '1002895376527', 1, 690989250, 690989250)

🔹 Таблица: server_settings
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - name: TEXT NOT NULL
     - ip: TEXT
     - url: TEXT NOT NULL
     - port: TEXT NOT NULL
     - secret_path: TEXT NOT NULL
     - username: TEXT NOT NULL
     - password: TEXT NOT NULL
     - secretkey: TEXT
     - inbound_id: INTEGER
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
     - inbound_id_promo: INTEGER DEFAULT 2
     - protocol: TEXT DEFAULT 'vless'
   📊 Количество записей: 3
   📝 Примеры записей:
     1. (2, 'Нидерланды 🇳🇱', '64.188.97.159', 'htt tps://64.188.97.159', '29241', 'jWkWSQV3YADnZ8B', 'K3USRz9O63', 'QNNrvZUw4m', '', 5, 1, 2, 'vless')      
     2. (3, 'Германия 🇩🇪', '213.21.241.227', 'http ps://213.21.241.227', '31210', 'Ez2rVj5nQJaZeNw', 'KTZmwFGyA3', 'McNbcNRS7Y', '', 1, 1, 2, 'vless')      
     3. (4, 'Trojan 🇩🇪', '213.21.241.227', 'https: ://213.21.241.227', '31210', 'Ez2rVj5nQJaZeNw', 'KTZmwFGyA3', 'McNbcNRS7Y', '', 4, 0, 2, 'vless')        

🔹 Таблица: sqlite_sequence
   Столбцы:
     - name:
     - seq:
   📊 Количество записей: 20
   📝 Примеры записей:
     1. ('support_info', 1)
     2. ('yookassa_settings', 3)
     3. ('user', 553)

🔹 Таблица: bot_message
   Столбцы:
     - command: TEXT (PRIMARY KEY)
     - text: TEXT NOT NULL
     - image_path: TEXT
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
   📊 Количество записей: 13
   📝 Примеры записей:
     1. ('admin', 'Вы в админ-меню. Выберите действие:', 'static/images/new/admin.png', 1)
     2. ('start', '👋🏻 <b>Добро пожаловать в TOR VPN !</b>&#10;\n✔️ <b>Бот для быстрой покупки VPN\n⚡  Моментальная выдача\n🔒 Надёжная защита\n📱 Подходит для любых устройств</b>\n', 'static/images/new/start.png', 1)
     3. ('user_lk', '👤 <b>Ваш личный профиль!</b>&#10;\n<blockquote>📋 <b>Мои подписки</b> — Активные ключи\n💳 <b>Мои платежи</b> — Пополнения и расходы\n💰 <b>Мой баланс</b> — Текущий остаток\n🤝 <b>Мои рефералы</b> — Бонусы за приглашения\n⏳ <b>Продлить VPN</b> — Продление подписки\n🚀 <b>Автоподключение V2RayTun</b> — Быстрое автоматическое соединение\n</blockquote>&#10;', 'static/images/new/profile.png', 1)

🔹 Таблица: user
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - username: TEXT
     - telegram_id: INTEGER NOT NULL
     - trial_period: BOOLEAN DEFAULT 0
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
     - date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP    
     - referral_code: TEXT
     - referral_count: INTEGER DEFAULT 0
     - referred_by: TEXT
     - name_accunt: TEXT
     - name_account: TEXT
   📊 Количество записей: 549
   📝 Примеры записей:
     1. (1, 'ovspd', 753514362, 0, 1, '2025-03-03 08:20:59', '6DM3ATNM', 0, None, None, None)
     2. (2, 'sannilo', 690989250, 1, 1, '2025-06-23 22:59:41', 'HY70TYZB', 159, None, None, 'Санни')    
     3. (3, 'TOR_VPNbot', 7580464478, 0, 1, '2025-06-24 01:48:55', 'P6DQR6UC', 0, None, None, 'TOR VPN | Bot ⚡️')

🔹 Таблица: tariff
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - name: TEXT NOT NULL
     - description: TEXT
     - price: DECIMAL(10,2) NOT NULL
     - left_day: INTEGER NOT NULL
     - server_id: INTEGER NOT NULL
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
   📊 Количество записей: 8
   📝 Примеры записей:
     1. (9, '1 месяц 🥉', 'До 100Mb/сек\n<b>Трафик:</b> Безлимит в месяц', 75, 30, 2, 1)
     2. (10, '3 месяца 🥇', 'До 100Mb/сек\n<b>Трафик:</b> Безлимит в месяц\n<b>Цена за месяц</b> 70 ₽', 210, 90, 2, 1)
     3. (11, '2 месяца 🥈', 'До 100Mb/сек\n<b>Трафик:</b> Безлимит в месяц\n<b>Цена за месяц:</b> 72,5 ₽', 145, 60, 2, 1)

🔹 Таблица: trial_settings
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - name: TEXT NOT NULL
     - left_day: INTEGER NOT NULL
     - server_id: INTEGER NOT NULL
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
   📊 Количество записей: 1
   📝 Примеры записей:
     1. (1, '↙️↙️↙️\r\n<b>🎁 Пробный тариф🎁</b>\r\n  n<b>Трафик:</b> Безлимит ♾️ ', 2, 3, 1)

🔹 Таблица: user_subscription
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - user_id: INTEGER NOT NULL
     - tariff_id: INTEGER NOT NULL
     - server_id: INTEGER NOT NULL
     - start_date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     - end_date: TIMESTAMP NOT NULL
     - vless: TEXT
     - is_active: BOOLEAN NOT NULL DEFAULT 1        
     - payment_id: TEXT
   📊 Количество записей: 271
   📝 Примеры записей:
     1. (12, 5080736898, 106, 2, '2025-06-27 08:02:09', '2025-06-30 10:02:07.968031', 'vless://7b1c9772-56b2-495a-aff3-28b1ad1ef031@64.188.97.159:443?type=tcp&security=reality&pbk=VAlda-3_c1JjlxXjcfCT2P3x3u99w-ALodoB20tgbB8&fp=chrome&sni=google.com&sid=533ae1632e28&spx=/&flow=xtls-rprx-vision#TOR VPN⚡| tg_5080736898@28365', 1, None)
     2. (13, 788605856, 106, 2, '2025-06-27 08:27:01', '2025-06-30 10:27:01.555824', 'vless://86a8870d-f766-43a6-947a-3f39cfa9dbd3@64.188.97.159:443?type=tcp&security=reality&pbk=VAlda-3_c1JjlxXjcfCT2P3x3u99w-ALodoB20tgbB8&fp=chrome&sni=google.com&sid=533ae1632e28&spx=/&flow=xtls-rprx-vision#TOR VPN⚡| tg_788605856@60826', 1, None)
     3. (15, 906619006, 10, 2, '2025-06-27 10:43:59', '2025-09-28 12:43:58.246767', 'vless://79c59a5d-cf95-48a1-a4e9-5e9cd3e25aea@64.188.97.159:443?type=tcp&security=reality&pbk=VAlda-3_c1JjlxXjcfCT2P3x3u99w-ALodoB20tgbB8&fp=chrome&sni=google.com&sid=533ae1632e28&spx=/&flow=xtls-rprx-vision#TOR VPN⚡| tg_906619006@29515', 1, '2ff08951-000f-5001-9000-16fe4585874e')

🔹 Таблица: yookassa_settings
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - name: TEXT
     - shop_id: TEXT NOT NULL
     - api_key: TEXT NOT NULL
     - description: TEXT
     - is_enable: INTEGER DEFAULT 0
   📊 Количество записей: 2
   📝 Примеры записей:
     1. (2, 'TN  Compny INC.', '1050392', 'live_Iyd9AT2EBtoejWV4eWluA_nRZaYKha0MJp9okFQ5VUc', '', 1)    
     2. (3, 'TN  Compny INC', '1113883', 'live_SgFbg5OS1kFY3TnHmew4Qwt6TaMlkKUL3mz38F7D0qs', '', 0)     

🔹 Таблица: promocodes
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - promocod: TEXT NOT NULL
     - activation_limit: INTEGER DEFAULT 1
     - activation_total: INTEGER DEFAULT 0
     - percentage: DECIMAL(5,2) NOT NULL
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
     - date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP    
   📊 Количество записей: 8
   📝 Примеры записей:
     1. (2, '8YD9XMHXI6Z2', 6, 1, 25, 1, '2025-06-24 06:58:38')
     2. (3, 'START25', 5, 1, 25, 1, '2025-06-27 06:55:50')
     3. (4, 'SANNI_START25', 5, 0, 25, 1, '2025-06-27 06:56:57')

🔹 Таблица: payments
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - user_id: INTEGER NOT NULL
     - tariff_id: INTEGER NOT NULL
     - price: REAL NOT NULL
     - date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP    
   📊 Количество записей: 133
   📝 Примеры записей:
     1. (1, 5155251529, 3, 100.0, '2025-06-25 05:39:13')
     2. (2, 5155251529, 3, 100.0, '2025-06-25 05:44:26')
     3. (3, 5155251529, 12, 1.0, '2025-06-27 06:35:54')

🔹 Таблица: support_info
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - message: TEXT NOT NULL
     - bot_version: TEXT NOT NULL
     - support_url: TEXT NOT NULL
   📊 Количество записей: 1
   📝 Примеры записей:
     1. (1, 'Подробное описание бота и прием заявок Вы можете найти на сайте', '1.0.1', 'https://t.me/slickux')

🔹 Таблица: notify_settings
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - name: TEXT NOT NULL
     - interval: INTEGER NOT NULL
     - type: TEXT NOT NULL
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
   📊 Количество записей: 1
   📝 Примеры записей:
     1. (1, '‼️ Срок подписки:', 180, 'subscription__check', 1)

🔹 Таблица: tariff_promo
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - name: TEXT NOT NULL
     - description: TEXT
     - left_day: INTEGER NOT NULL
     - server_id: INTEGER
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
   📊 Количество записей: 2
   📝 Примеры записей:
     1. (2, 'PROMO ♻️', 'Промо тариф от Администрациии!', 15, 2, 1)
     2. (3, '🏆 Приз за 1 место.', 'Участие в конкурсе.', 90, 2, 1)

🔹 Таблица: Reviews
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - username: TEXT NOT NULL
     - message: TEXT NOT NULL
     - date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP    
   📊 Количество записей: 0

🔹 Таблица: payments_code
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - pay_code: TEXT NOT NULL
     - sum: DECIMAL(10,2) NOT NULL
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
     - create_date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   📊 Количество записей: 1
   📝 Примеры записей:
     1. (3, 'MK37T7489P1B', 75, 1, '2025-07-10 22:34:18')

🔹 Таблица: crypto_settings
   Столбцы:
     - api_token: TEXT NOT NULL
     - is_enable: BOOLEAN DEFAULT 0
     - min_amount: DECIMAL(10,2) DEFAULT 1.00       
     - supported_assets: TEXT
     - webhook_url: TEXT
     - webhook_secret: TEXT
   📊 Количество записей: 1
   📝 Примеры записей:
     1. ('419536:AAhv0z9hmR5ln7nTYkKkiwuxIgZckmVWR9a', 1, 0.88, '["USDT", "TON", "SOL", "TRX", "GRAM", "BTC", "ETH", "DOGE", "LTC", "NOT", "TRUMP", "MELANIA", "PEPE", "WIF", "BONK", "MAJOR", "MY", "DOGS", "MEMHASH", "BNB", "HMSTR", "CATI", "USDC", "RUB", "USD", "EUR", "BYN", "UAH", "GBP", "CNY", "KZT", "UZS", "GEL", "TRY", "AMD", "THB", "INR", "BRL", "IDR", "AZN", "AED", "PLN", "ILS", "KGS", "TJS"]', None, None) 

🔹 Таблица: raffles
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - name: TEXT NOT NULL
     - description: TEXT
     - start_date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     - end_date: TIMESTAMP
     - status: TEXT DEFAULT 'active'
     - winner_ticket_id: INTEGER
   📊 Количество записей: 3
   📝 Примеры записей:
     1. (1, '6 месяцев VPN 😱', '🔒 Получи 6 месяцев бесплатного VPN — полная защита, полная свобода! Участвуй в розыгрыше и будь в безопасности в интернете 😎', '2025-06-24 06:28:01', '2025-06-28 06:59:29', 'inactive', None)
     2. (2, 'Розыгрыш VPN', '🎉 Розыгрыш VPN-доступа!\n🏆 3 призовых места:\n\n1️⃣ место — 6 месяцев VPN N\n2️⃣ место — 3 месяца VPN\n3️⃣ место — 1 месяц VPN\   \n\nЧтобы принять участие, необходимо иметь активную подписку.\n\n📌 Начисление билетов:\n\n▫️ 1 месяц —  1 билет\n▫️ 3 месяца — 4 билета\n▫️ 6 месяцев — 9 би илетов\n\n🔹 Минимум для участия — 2 билета\n🔹 Дополнительные билеты можно получить, оформляя новые подписки\n\n🎫 Больше билетов — выше шансы на победу!', '2025-06-28 06:59:00', '2025-06-28 06:59:29', 'inactive', None)
     3. (3, 'Розыгрыш VPN', '🎉 Розыгрыш VPN-доступа!\n🏆 3 призовых места:\n\n1️⃣ место — 6 месяцев VPN N\n2️⃣ место — 3 месяца VPN\n3️⃣ место — 1 месяц VPN\   \n\nЧтобы принять участие, необходимо иметь активную подписку.\n\n📌 Начисление билетов:\n\n▫️ 1 месяц —  1 билет\n▫️ 3 месяца — 4 билета\n▫️ 6 месяцев — 9 би илетов\n\n🔹 Минимум для участия — 2 билета\n🔹 Дополнительные билеты можно получить, оформляя новые подписки\n\n🎫 Больше билетов — выше шансы на победу!', '2025-06-28 07:00:09', '2025-06-28 15:21:41', 'inactive', None)

🔹 Таблица: raffle_tickets
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - user_id: INTEGER NOT NULL
     - telegram_id: INTEGER NOT NULL
     - ticket_number: TEXT NOT NULL
     - created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     - raffle_id: INTEGER
   📊 Количество записей: 0

🔹 Таблица: user_balance
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - user_id: INTEGER NOT NULL
     - balance: DECIMAL(10,2) DEFAULT 0.00
     - last_update: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   📊 Количество записей: 61
   📝 Примеры записей:
     1. (1, 100000001, 10, '2025-06-23 22:42:34')   
     2. (2, 690989250, 1162.06, '2025-08-16 20:46:41')
     3. (3, 5155251529, 4838.060000000001, '2025-08-22 01:55:03')

🔹 Таблица: balance_transactions
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - user_id: INTEGER NOT NULL
     - amount: DECIMAL(10,2) NOT NULL
     - type: TEXT NOT NULL
     - description: TEXT
     - payment_id: TEXT
     - created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   📊 Количество записей: 215
   📝 Примеры записей:
     1. (16, 733276263, 210, 'deposit', 'Пополнение баланса на сумму 210.0 руб.', '2ff1a79f-000f-5001-9000-1d657f3e58d3', '2025-06-28 07:29:22')
     2. (21, 841812734, 100, 'deposit', 'Пополнение баланса на сумму 100.0 руб.', '2ff0ee12-000f-5001-8000-10f9d22ed1ee', '2025-06-28 21:53:46')
     3. (22, 733276263, 210, 'deposit', 'Пополнение баланса на сумму 210.0 руб.', '2ff1a79f-000f-5001-9000-1d657f3e58d3', '2025-06-28 21:54:23')

🔹 Таблица: crypto_payments
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - user_id: INTEGER NOT NULL
     - tariff_id: INTEGER NOT NULL
     - invoice_id: TEXT NOT NULL
     - amount: DECIMAL(10,2) NOT NULL
     - asset: TEXT NOT NULL
     - status: TEXT NOT NULL
     - created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
     - updated_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   📊 Количество записей: 7
   📝 Примеры записей:
     1. (1, 690989250, 3, '28234541', 100, 'USDT', 'pending', '2025-06-24 05:55:45', '2025-06-24 05:55:45')
     2. (2, 690989250, 3, '28278889', 100, 'USDT', 'pending', '2025-06-24 19:36:30', '2025-06-24 19:36:30')
     3. (3, 5155251529, 3, '28284206', 100, 'USDT', 'pending', '2025-06-24 21:03:38', '2025-06-24 21:03:38')

🔹 Таблица: referral_condition
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - name: TEXT NOT NULL
     - description: TEXT
     - invitations: INTEGER NOT NULL
     - reward_sum: DECIMAL(10,2) NOT NULL
     - is_enable: BOOLEAN NOT NULL DEFAULT 1        
     - created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   📊 Количество записей: 7
   📝 Примеры записей:
     1. (1, '🥉 sᴛᴀʀᴛ', '\r\n⚡ ҕыстᴘый стᴀᴘт, пᴇᴘвᴀя нᴀгᴘᴀдᴀ.', 3, 20, 1, '2025-07-20 14:00:20')       
     2. (2, '🪙 ʙʀᴏɴᴢᴇ', '\r\n👍 ʏжᴇ почти окʏпᴀᴇшь  подпискʏ.', 7, 50, 1, '2025-07-20 14:00:28')        
     3. (3, '🥈 sɪʟᴠᴇʀ', '\r\n🚀 твой пᴇᴘвый кᴘʏпный ҕонʏс.', 15, 120, 0, '2025-07-20 14:00:36')        

🔹 Таблица: referral_progress
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - user_id: INTEGER NOT NULL
     - total_invites: INTEGER DEFAULT 0
     - last_reward_at: TIMESTAMP
   📊 Количество записей: 553
   📝 Примеры записей:
     1. (1, 753514362, 0, None)
     2. (2, 690989250, 159, None)
     3. (3, 7580464478, 0, None)

🔹 Таблица: referral_rewards_history
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - user_id: INTEGER NOT NULL
     - condition_id: INTEGER NOT NULL
     - reward_sum: DECIMAL(10,2) NOT NULL
     - created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   📊 Количество записей: 6
   📝 Примеры записей:
     1. (5, 690989250, 4, 300, '2025-07-20 20:37:13')
     2. (6, 690989250, 3, 120, '2025-07-20 21:09:36')
     3. (7, 690989250, 2, 50, '2025-07-21 04:01:13')

🔹 Таблица: admin_notifications
   Столбцы:
     - id: INTEGER (PRIMARY KEY)
     - message: TEXT NOT NULL
     - date: TIMESTAMP DEFAULT CURRENT_TIMESTAMP    
     - is_read: BOOLEAN DEFAULT 0
   📊 Количество записей: 0

==================================================  
✅ Проверка завершена!