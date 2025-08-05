"""
Валидаторы для приложения shop
"""

import re
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .constants import MIN_ORDER_AMOUNT, MAX_ORDER_ITEMS, MAX_CART_ITEMS


def validate_phone_number(value):
    """Валидация номера телефона"""
    if not value:
        return
    
    # Убираем все символы кроме цифр
    digits_only = re.sub(r'\D', '', value)
    
    # Проверяем длину (украинские номера: 10-12 цифр)
    if len(digits_only) < 10 or len(digits_only) > 12:
        raise ValidationError(_('Номер телефона должен содержать от 10 до 12 цифр'))
    
    # Проверяем, что номер начинается с кода Украины или местного кода
    if not (digits_only.startswith('380') or digits_only.startswith('0')):
        raise ValidationError(_('Номер телефона должен начинаться с кода Украины (380) или местного кода (0)'))


def validate_order_amount(value):
    """Валидация суммы заказа"""
    if value < MIN_ORDER_AMOUNT:
        raise ValidationError(
            _('Минимальная сумма заказа составляет %(min_amount)s грн'),
            params={'min_amount': MIN_ORDER_AMOUNT}
        )


def validate_order_items_count(value):
    """Валидация количества товаров в заказе"""
    if value > MAX_ORDER_ITEMS:
        raise ValidationError(
            _('Максимальное количество товаров в заказе: %(max_items)s'),
            params={'max_items': MAX_ORDER_ITEMS}
        )


def validate_cart_items_count(value):
    """Валидация количества товаров в корзине"""
    if value > MAX_CART_ITEMS:
        raise ValidationError(
            _('Максимальное количество товаров в корзине: %(max_items)s'),
            params={'max_items': MAX_CART_ITEMS}
        )


def validate_positive_decimal(value):
    """Валидация положительного десятичного числа"""
    if value <= 0:
        raise ValidationError(_('Значение должно быть больше нуля'))


def validate_nova_poshta_city_ref(value):
    """Валидация City Ref для Nova Poshta"""
    if not value:
        return
    
    # City Ref должен быть UUID формата
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, value, re.IGNORECASE):
        raise ValidationError(_('City Ref должен быть в формате UUID'))


def validate_nova_poshta_warehouse_ref(value):
    """Валидация Warehouse Ref для Nova Poshta"""
    if not value:
        return
    
    # Warehouse Ref должен быть UUID формата
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if not re.match(uuid_pattern, value, re.IGNORECASE):
        raise ValidationError(_('Warehouse Ref должен быть в формате UUID'))


def validate_email_domain(value):
    """Валидация домена email"""
    if not value:
        return
    
    # Проверяем, что email содержит @
    if '@' not in value:
        raise ValidationError(_('Email должен содержать символ @'))
    
    # Проверяем, что после @ есть домен
    domain = value.split('@')[1]
    if not domain or '.' not in domain:
        raise ValidationError(_('Email должен содержать корректный домен'))


def validate_payment_amount(value, order_total):
    """Валидация суммы платежа"""
    if value != order_total:
        raise ValidationError(
            _('Сумма платежа (%(payment_amount)s) должна соответствовать сумме заказа (%(order_amount)s)'),
            params={
                'payment_amount': value,
                'order_amount': order_total
            }
        )


def validate_webhook_signature(signature, expected_signature, system):
    """Валидация подписи webhook"""
    if signature != expected_signature:
        raise ValidationError(
            _('Неверная подпись webhook для %(system)s'),
            params={'system': system}
        )


def validate_order_status_transition(old_status, new_status):
    """Валидация перехода статуса заказа"""
    valid_transitions = {
        'pending': ['processing', 'cancelled'],
        'processing': ['completed', 'cancelled'],
        'completed': [],  # завершенный заказ нельзя изменить
        'cancelled': [],  # отмененный заказ нельзя изменить
    }
    
    if new_status not in valid_transitions.get(old_status, []):
        raise ValidationError(
            _('Недопустимый переход статуса с "%(old_status)s" на "%(new_status)s"'),
            params={
                'old_status': old_status,
                'new_status': new_status
            }
        )


def validate_payment_status_transition(old_status, new_status):
    """Валидация перехода статуса платежа"""
    valid_transitions = {
        'pending': ['paid', 'failed'],
        'paid': ['refunded'],
        'failed': ['pending'],  # можно повторить
        'refunded': [],  # возврат - финальное состояние
    }
    
    if new_status not in valid_transitions.get(old_status, []):
        raise ValidationError(
            _('Недопустимый переход статуса платежа с "%(old_status)s" на "%(new_status)s"'),
            params={
                'old_status': old_status,
                'new_status': new_status
            }
        ) 