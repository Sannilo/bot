"""Обработчик страницы профиля"""
from flask import render_template, jsonify
from bd import DB

class ProfileHandler:
    @staticmethod
    def handle(user_id):
        """Обработка страницы профиля"""
        return render_template('profile.html', user_id=user_id)

    @staticmethod
    def get_user_profile_data(user_id):
        """Получить данные профиля пользователя"""
        return DB.get_user_profile_data(user_id)

    @staticmethod
    def get_user_subscriptions_data(user_id):
        """Получить данные о подписках пользователя"""
        return DB.get_user_subscriptions_data(user_id)
