from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
import aiosqlite
import os
from datetime import datetime, timedelta
from handlers.database import db

from handlers.x_ui import xui_manager
from handlers.user.user_kb import get_subscriptions_keyboard, get_success_by_keyboard
from handlers.yookassa import yookassa_manager
from asyncio import Lock

async def send_renewal_notification_to_admin(bot, user_id, username, tariff_days, tariff_info, payment_method):
    """Отправка уведомления администратору о продлении подписки"""
    try:
        bot_settings = await db.get_bot_settings()
        if not bot_settings or not bot_settings.get('admin_id'):
            logger.warning("Не найдены ID администраторов в базе данных")
            return
            
        admin_ids = bot_settings['admin_id']
        username = username or "Не указан"
        
        if tariff_info:
            try:
                tariff_name = str(tariff_info['name'])
                server_name = str(tariff_info['server_name'])
                tariff_price = str(tariff_info['price'])
            except (KeyError, IndexError):
                tariff_name, server_name, tariff_price = 'Неизвестный тариф', 'Неизвестный сервер', 'Не указана'
        else:
            tariff_name, server_name, tariff_price = 'Неизвестный тариф', 'Неизвестный сервер', 'Не указана'
            
        days_text = str(tariff_days) if tariff_days is not None else "Неизвестно"
        price_text = str(tariff_price) if tariff_price is not None else "Не указана"
        
        message = (
            "✅ <b>Новое продление подписки</b>\n\n"
            f"<b>👤 Пользователь:</b> <code>{user_id}</code> (@{username})\n"
            f"<blockquote><b>📝 Тариф:</b> {tariff_name}\n"
            f"<b>🌐 Сервер:</b> {server_name}\n"
            f"<b>📅 Продлено на:</b> {days_text} дней\n"
            f"<b>💳 Способ оплаты:</b> {payment_method}\n"
            f"<b>💰 Сумма:</b> {price_text} руб.\n"
            f"<b>🕒 Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</blockquote>"
        )
        
        for admin_id in admin_ids:
            try:
                await bot.send_message(int(admin_id), message, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления админу {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления о продлении: {e}")

router = Router()

payment_locks = {}

async def extend_subscription_in_xui(server_settings, vless_link, new_end_date):
    """Продление подписки в X-UI с поиском по email во всех inbound"""
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
        target_inbound = None
        
        # Поиск клиента
        for inbound in inbounds:
            if hasattr(inbound, 'settings') and hasattr(inbound.settings, 'clients'):
                clients = inbound.settings.clients
                found = next((c for c in clients if c.id == client_id), None)
                if found:
                    target_client, target_inbound = found, inbound
                    logger.info(f"Клиент найден по ID {client_id} в inbound {inbound.id}")
                    break
                if email:
                    found = next((c for c in clients if hasattr(c, 'email') and c.email == email), None)
                    if found:
                        target_client, target_inbound = found, inbound
                        logger.info(f"Клиент найден по email {email} в inbound {inbound.id}")
                        break
        
        if not target_client:
            logger.error(f"Клиент не найден ни по ID {client_id}, ни по email {email} на сервере {server_settings['id']}")
            
            # --- ОТЛАДОЧНЫЙ ВЫВОД ---
            logger.warning("--- НАЧАЛО СПИСКА КЛИЕНТОВ НА СЕРВЕРЕ (для отладки) ---")
            any_client_found = False
            for i, inbound in enumerate(inbounds):
                if hasattr(inbound, 'settings') and hasattr(inbound.settings, 'clients'):
                    clients_in_inbound = inbound.settings.clients
                    if clients_in_inbound:
                        any_client_found = True
                        logger.info(f"Клиенты в Inbound ID: {inbound.id}")
                        for c in clients_in_inbound:
                            logger.info(f"  -> ID: {c.id}, Email: {getattr(c, 'email', 'N/A')}")
            if not any_client_found:
                logger.warning("На сервере не найдено ни одного клиента ни в одном inbound.")
            logger.warning("--- КОНЕЦ СПИСКА КЛИЕНТОВ НА СЕРВЕРЕ ---")
            # --- КОНЕЦ ОТЛАДКИ ---

            return False
        
        new_expiry = int(new_end_date.timestamp() * 1000)
        
        target_client.expiry_time = new_expiry
        
        try:
            client.client.update(target_client.id, target_client)
            logger.info(f"Клиент {getattr(target_client, 'email', target_client.id)} успешно обновлен в inbound {target_inbound.id}. Новая дата истечения: {new_end_date}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при вызове client.client.update для {target_client.id}: {e}")
            return False
        
    except Exception as e:
        logger.error(f"Ошибка при продлении подписки в X-UI: {e}")
        return False

class RenewSubscriptionStates(StatesGroup):
    waiting_for_subscription_selection = State()
    waiting_for_tariff_selection = State()
    waiting_for_payment = State()

@router.callback_query(F.data == "renew_subscription")
async def process_renew_subscription(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки продления подписки"""
    try:
        await callback.message.delete()
        
        time_threshold = datetime.now() + timedelta(minutes=15)
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT 
                    us.*,
                    s.name as server_name,
                    CAST((julianday(us.end_date) - julianday('now', 'localtime')) * 86400 AS INTEGER) as seconds_left
                FROM user_subscription us
                JOIN server_settings s ON us.server_id = s.id
                WHERE us.user_id = ? AND us.is_active = 1 AND us.end_date > ?
                ORDER BY us.end_date DESC
            """, (callback.from_user.id, time_threshold.strftime('%Y-%m-%d %H:%M:%S'))) as cursor:
                subscriptions = await cursor.fetchall()
        
        if not subscriptions:
            await callback.message.answer(
                "У вас нет активных подписок для продления.",
                reply_markup=get_subscriptions_keyboard()
            )
            return
        
        if len(subscriptions) == 1:
            await state.update_data(subscription_id=subscriptions[0]['id'],
                                    server_id=subscriptions[0]['server_id'],
                                    vless=subscriptions[0]['vless'],
                                    end_date=subscriptions[0]['end_date'])
            await show_tariffs_for_renewal(callback, state)
            return
        
        keyboard = InlineKeyboardBuilder()
        
        for sub in subscriptions:
            total_seconds = sub['seconds_left'] if sub['seconds_left'] > 0 else 0

            time_str = ''
            if total_seconds >= 86400:
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                time_str = f"{days}д {hours}ч"
            elif total_seconds >= 3600:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                time_str = f"{hours}ч {minutes}м"
            else:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                time_str = f"{minutes}м {seconds}с"
            
            server_name = sub['server_name']
            server_flag = server_name.split(' ')[-1] if ' ' in server_name else server_name
            
            vless_link = sub['vless']
            key_id = ''
            if '@' in vless_link:
                key_id = '@' + vless_link.split('@')[-1]
            
            button_text = f"{server_flag} | {time_str} | {key_id}"
            keyboard.button(text=button_text, callback_data=f"select_subscription_for_renewal:{sub['id']}")
        
        keyboard.button(text="🔙 Назад", callback_data="lk_my_subscriptions")
        keyboard.adjust(1)
        
        message_data = await db.get_bot_message('usd_tariff_user')
        
        if message_data and message_data['image_path'] and os.path.exists(message_data['image_path']):
            await callback.message.answer_photo(
                photo=FSInputFile(message_data['image_path']),
                caption=message_data['text'],
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )
        else:
            text = message_data['text'] if message_data else "Выберите подписку для продления:"
            await callback.message.answer(text=text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        
        await state.set_state(RenewSubscriptionStates.waiting_for_subscription_selection)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки продления подписки: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.", reply_markup=get_subscriptions_keyboard())

@router.callback_query(F.data.startswith("select_subscription_for_renewal:"))
async def process_subscription_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора подписки для продления"""
    try:
        await callback.message.delete()
        subscription_id = int(callback.data.split(":")[1])
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM user_subscription WHERE id = ? AND is_active = 1", (subscription_id,)) as cursor:
                subscription = await cursor.fetchone()
        
        if not subscription:
            await callback.message.answer("Подписка не найдена или неактивна.", reply_markup=get_subscriptions_keyboard())
            return
        
        await state.update_data(subscription_id=subscription_id,
                                server_id=subscription['server_id'],
                                vless=subscription['vless'],
                                end_date=subscription['end_date'])
        
        await show_tariffs_for_renewal(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка при выборе подписки для продления: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.", reply_markup=get_subscriptions_keyboard())

async def show_tariffs_for_renewal(callback: CallbackQuery, state: FSMContext):
    """Отображение тарифов для продления подписки"""
    try:
        data = await state.get_data()
        server_id = data.get('server_id')
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM server_settings WHERE id = ?", (server_id,)) as cursor:
                server = await cursor.fetchone()
            async with conn.execute("SELECT * FROM tariff WHERE server_id = ? AND is_enable = 1 ORDER BY left_day", (server_id,)) as cursor:
                tariffs = await cursor.fetchall()

        if not server or not tariffs:
            await callback.message.answer("Сервер или тарифы не найдены.", reply_markup=get_subscriptions_keyboard())
            return
        
        await state.set_state(RenewSubscriptionStates.waiting_for_tariff_selection)
        
        server_name = server['name']
        server_flag = server_name.split(' ')[-1] if ' ' in server_name else server_name
        text = f"🌍 Сервер: {server_flag}\n\nДоступные тарифные планы для продления:\n\n"
        
        for tariff in tariffs:
            text += (f"<blockquote><b>Тариф:</b> {tariff['name']}\n"
                     f"<b>Описание:</b> {tariff['description']}\n"
                     f"<b>Стоимость:</b> {tariff['price']} руб.\n"
                     f"<b>Срок:</b> {tariff['left_day']} дней</blockquote>")
        
        keyboard = InlineKeyboardBuilder()
        for tariff in tariffs:
            keyboard.button(text=f"{tariff['name']} - {tariff['price']} ₽", callback_data=f"renew_tariff:{tariff['id']}")
        
        keyboard.button(text="🔙 Назад", callback_data="lk_my_subscriptions")
        keyboard.adjust(2, 2, 1)
        
        await callback.message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка при отображении тарифов для продления: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.", reply_markup=get_subscriptions_keyboard())

@router.callback_query(F.data.startswith("renew_tariff:"), RenewSubscriptionStates.waiting_for_tariff_selection)
async def process_renew_tariff_selection(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора тарифа для продления"""
    try:
        await callback.message.delete()
        tariff_id = int(callback.data.split(":")[1])
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM tariff WHERE id = ?", (tariff_id,)) as cursor:
                tariff = await cursor.fetchone()
        
        if not tariff:
            await callback.message.answer("Выбранный тариф не найден.", reply_markup=get_subscriptions_keyboard())
            return
        
        await state.update_data(tariff_id=tariff_id,
                                tariff_days=tariff['left_day'],
                                tariff_price=tariff['price'])
        
        await show_payment_menu_for_renewal(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка при выборе тарифа для продления: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.", reply_markup=get_subscriptions_keyboard())

async def show_payment_menu_for_renewal(callback: CallbackQuery, state: FSMContext):
    """Отображение меню оплаты для продления подписки"""
    try:
        data = await state.get_data()
        tariff_id = data.get('tariff_id')
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT t.*, s.name as server_name FROM tariff t JOIN server_settings s ON t.server_id = s.id WHERE t.id = ?", (tariff_id,)) as cursor:
                tariff = await cursor.fetchone()
        
        if not tariff:
            await callback.message.answer("Выбранный тариф недоступен.", reply_markup=get_subscriptions_keyboard())
            return
        
        await state.set_state(RenewSubscriptionStates.waiting_for_payment)
        
        server_name = tariff['server_name']
        server_flag = server_name.split(' ')[-1] if ' ' in server_name else server_name
        message_text = (f"Выберите способ оплаты:\n"
                        f"<blockquote><b>Тариф:</b> {tariff['name']}\n"
                        f"<b>Описание:</b> {tariff['description']}\n"
                        f"<b>Стоимость:</b> {tariff['price']} руб.\n"
                        f"<b>Страна:</b> {server_flag}\n"
                        f"<b>Срок:</b> {tariff['left_day']} дней.</blockquote>")
        
        keyboard = InlineKeyboardBuilder()
        if await db.is_yookassa_enabled():
            keyboard.button(text="🔵 Карты РФ/СБП", callback_data=f"renew_pay_yookassa:{tariff['price']}")
        
        keyboard.button(text="💲 С баланса", callback_data=f"renew_pay_balance:{tariff['price']}")
        keyboard.button(text="🔙 Отмена", callback_data="lk_my_subscriptions")
        keyboard.adjust(2, 1)
        
        await callback.message.answer(message_text, reply_markup=keyboard.as_markup(), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка при отображении меню оплаты для продления: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.", reply_markup=get_subscriptions_keyboard())

@router.callback_query(F.data.startswith("renew_pay_balance:"), RenewSubscriptionStates.waiting_for_payment)
async def process_renew_pay_balance(callback: CallbackQuery, state: FSMContext):
    """Обработчик оплаты с баланса для продления подписки"""
    try:
        await callback.message.delete()
        
        data = await state.get_data()
        tariff_price = data.get('tariff_price')
        tariff_days = data.get('tariff_days')
        
        user_balance = await db.get_user_balance(callback.from_user.id)
        
        if user_balance < tariff_price:
            await callback.message.answer("Недостаточно средств на балансе.", reply_markup=get_subscriptions_keyboard())
            return
        
        await db.update_balance(callback.from_user.id, -tariff_price, "renewal", f"Продление подписки на {tariff_days} дней")
        await state.update_data(payment_method="Баланс")
        await process_subscription_renewal(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка при оплате с баланса для продления: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.", reply_markup=get_subscriptions_keyboard())

@router.callback_query(F.data.startswith("renew_pay_yookassa:"), RenewSubscriptionStates.waiting_for_payment)
async def process_renew_pay_yookassa(callback: CallbackQuery, state: FSMContext):
    """Обработчик оплаты через ЮКассу для продления подписки"""
    try:
        await callback.message.delete()
        
        data = await state.get_data()
        tariff_price = data.get('tariff_price')
        tariff_days = data.get('tariff_days')
        
        payment_result = await yookassa_manager.create_payment(
            amount=tariff_price,
            description=f"Продление подписки на {tariff_days} дней (ID: {callback.from_user.id})",
            user_id=str(callback.from_user.id),
            username=callback.from_user.username,
            name_account=callback.from_user.full_name
        )
        
        if not payment_result or not payment_result[0] or not payment_result[1]:
            await callback.message.answer("Не удалось создать платеж.", reply_markup=get_subscriptions_keyboard())
            return
        
        payment_id, payment_url = payment_result
        await state.update_data(payment_id=payment_id)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="💰 Оплатить", url=payment_url)
        keyboard.button(text="✅ Я оплатил", callback_data=f"renew_check_payment:{payment_id}")
        keyboard.button(text="🔙 Отмена", callback_data="lk_my_subscriptions")
        keyboard.adjust(1)
        
        await callback.message.answer(
            "💳 *Ваш счет готов!*\n\n"
            "1️⃣ Нажмите *«💰Оплатить»*\n"
            "2️⃣ После оплаты нажмите *«✅ Я оплатил»*",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при создании платежа ЮКасса для продления: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.", reply_markup=get_subscriptions_keyboard())

@router.callback_query(F.data.startswith("renew_check_payment:"))
async def process_renew_check_payment(callback: CallbackQuery, state: FSMContext):
    """Обработчик проверки платежа для продления подписки"""
    try:
        payment_id = callback.data.split(":")[1]
        payment_status = await yookassa_manager.check_payment(payment_id)
        
        if not payment_status:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔄 Проверить еще раз", callback_data=f"renew_check_payment:{payment_id}")
            keyboard.button(text="🔙 Отмена", callback_data="lk_my_subscriptions")
            keyboard.adjust(1)
            await callback.answer("Платеж еще не поступил.", show_alert=True)
            return
        
        await callback.message.delete()
        await state.update_data(payment_method="ЮКасса")
        await process_subscription_renewal(callback, state)
        
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа для продления: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.", reply_markup=get_subscriptions_keyboard())

async def process_subscription_renewal(callback: CallbackQuery, state: FSMContext):
    """Продление подписки после успешной оплаты"""
    try:
        data = await state.get_data()
        tariff_days = data.get('tariff_days')
        subscription_id = data.get('subscription_id')
        vless = data.get('vless')
        server_id = data.get('server_id')
        end_date_str = data.get('end_date')
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT * FROM server_settings WHERE id = ?", (server_id,)) as cursor:
                server = await cursor.fetchone()
        
        if not server:
            await callback.message.answer("Сервер не найден.", reply_markup=get_subscriptions_keyboard())
            return
        
        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        
        current_time = datetime.now()
        if end_date < current_time:
            end_date = current_time
        
        new_end_date = end_date + timedelta(days=tariff_days)
        
        server_settings = dict(server)
        success = await extend_subscription_in_xui(server_settings, vless, new_end_date)
        
        if not success:
            await callback.message.answer(
                "Не удалось продлить подписку в X-UI. Обратитесь в поддержку.",
                reply_markup=get_subscriptions_keyboard()
            )
            return
        
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("UPDATE user_subscription SET end_date = ?, is_active = 1 WHERE id = ?",
                               (new_end_date.strftime('%Y-%m-%d %H:%M:%S'), subscription_id))
            await conn.commit()
        
        tariff_id = data.get('tariff_id')
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("SELECT t.*, s.name as server_name FROM tariff t JOIN server_settings s ON t.server_id = s.id WHERE t.id = ?", (tariff_id,)) as cursor:
                tariff_info = await cursor.fetchone()
        
        payment_method = data.get('payment_method', 'Баланс')
        
        await send_renewal_notification_to_admin(
            callback.bot, 
            callback.from_user.id, 
            callback.from_user.username, 
            tariff_days, 
            tariff_info, 
            payment_method
        )
        
        success_message = (
            "🎉 <b>Подписка успешно продлена!</b>\n\n"
            f"<blockquote>📅 <b>Новая дата окончания:</b> {new_end_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"⏰ <b>Продлено на:</b> {tariff_days} дней\n"
        )
        
        if tariff_info:
            success_message += (
                f"📦 <b>Тарифный план:</b> {tariff_info['name']}\n"
                f"🌍 <b>Сервер:</b> {tariff_info['server_name']}\n"
            )
        
        success_message += "</blockquote>\n\n✨ Ваш VPN-доступ снова активен!"
        
        await callback.message.answer(success_message, reply_markup=get_success_by_keyboard(), parse_mode="HTML")
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при продлении подписки: {e}")
        await callback.message.answer("Произошла ошибка. Обратитесь в поддержку.", reply_markup=get_subscriptions_keyboard())