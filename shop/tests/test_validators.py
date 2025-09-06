"""
Тесты для валидаторов
"""
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from shop.validators import (
    validate_order_status_transition,
    validate_payment_status_transition
)
from shop.models import Order, Payment

User = get_user_model()


class OrderStatusValidatorTests(TestCase):
    """Тесты для валидатора статусов заказов"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='USER'
        )
        
        self.order = Order.objects.create(
            user=self.user,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
    
    def test_valid_status_transitions(self):
        """Тест валидных переходов статусов"""
        valid_transitions = [
            ('pending', 'processing'),
            ('pending', 'cancelled'),
            ('processing', 'completed'),
            ('processing', 'cancelled'),
        ]
        
        for old_status, new_status in valid_transitions:
            with self.subTest(old_status=old_status, new_status=new_status):
                # Не должно вызывать исключение
                try:
                    validate_order_status_transition(old_status, new_status)
                except ValidationError:
                    self.fail(f"Transition from {old_status} to {new_status} should be valid")
    
    def test_invalid_status_transitions(self):
        """Тест невалидных переходов статусов"""
        invalid_transitions = [
            ('pending', 'completed'),  # Нельзя сразу завершить
            ('processing', 'pending'), # Нельзя вернуться назад
            ('completed', 'pending'),  # Завершенный нельзя изменить
            ('completed', 'processing'),
            ('completed', 'cancelled'),
            ('cancelled', 'pending'),  # Отмененный нельзя изменить
            ('cancelled', 'processing'),
            ('cancelled', 'completed'),
        ]
        
        for old_status, new_status in invalid_transitions:
            with self.subTest(old_status=old_status, new_status=new_status):
                with self.assertRaises(ValidationError) as context:
                    validate_order_status_transition(old_status, new_status)
                
                self.assertIn('Недопустимый переход статуса с', str(context.exception))
    
    def test_same_status_transition(self):
        """Тест перехода в тот же статус"""
        # Переход в тот же статус должен вызывать ошибку
        with self.assertRaises(ValidationError):
            validate_order_status_transition('pending', 'pending')
    
    def test_invalid_status_values(self):
        """Тест невалидных значений статусов"""
        invalid_statuses = ['invalid', '', None, 'unknown']
        
        for status in invalid_statuses:
            with self.subTest(status=status):
                with self.assertRaises(ValidationError):
                    validate_order_status_transition('pending', status)
    
    def test_validator_with_order_instance(self):
        """Тест валидатора с экземпляром заказа"""
        # Изменяем статус заказа
        self.order.status = 'processing'
        
        # Не должно вызывать исключение
        try:
            validate_order_status_transition('pending', 'processing')
        except ValidationError:
            self.fail("Valid status transition should not raise exception")


class PaymentStatusValidatorTests(TestCase):
    """Тесты для валидатора статусов платежей"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='USER'
        )
        
        self.order = Order.objects.create(
            user=self.user,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев'
        )
        
        self.payment = Payment.objects.create(
            order=self.order,
            amount=Decimal('100.00'),
            payment_system='stripe',
            status='pending'
        )
    
    def test_valid_payment_status_transitions(self):
        """Тест валидных переходов статусов платежей"""
        valid_transitions = [
            ('pending', 'paid'),
            ('pending', 'failed'),
            ('paid', 'refunded'),
        ]
        
        for old_status, new_status in valid_transitions:
            with self.subTest(old_status=old_status, new_status=new_status):
                try:
                    validate_payment_status_transition(old_status, new_status)
                except ValidationError:
                    self.fail(f"Payment transition from {old_status} to {new_status} should be valid")
    
    def test_invalid_payment_status_transitions(self):
        """Тест невалидных переходов статусов платежей"""
        invalid_transitions = [
            ('paid', 'pending'),    # Оплаченный нельзя вернуть в ожидание
            ('paid', 'failed'),     # Оплаченный нельзя сделать неудачным
            ('refunded', 'paid'),   # Возвращенный нельзя снова оплатить
            ('refunded', 'pending'),
            ('refunded', 'failed'),
        ]
        
        for old_status, new_status in invalid_transitions:
            with self.subTest(old_status=old_status, new_status=new_status):
                with self.assertRaises(ValidationError) as context:
                    validate_payment_status_transition(old_status, new_status)
                
                self.assertIn('Недопустимый переход статуса платежа', str(context.exception))
    
    def test_same_payment_status_transition(self):
        """Тест перехода в тот же статус платежа"""
        # Переход в тот же статус должен вызывать ошибку
        with self.assertRaises(ValidationError):
            validate_payment_status_transition('pending', 'pending')
    
    def test_invalid_payment_status_values(self):
        """Тест невалидных значений статусов платежей"""
        invalid_statuses = ['invalid', '', None, 'unknown']
        
        for status in invalid_statuses:
            with self.subTest(status=status):
                with self.assertRaises(ValidationError):
                    validate_payment_status_transition('pending', status)
    
    def test_validator_with_payment_instance(self):
        """Тест валидатора с экземпляром платежа"""
        # Изменяем статус платежа
        self.payment.status = 'paid'
        
        # Не должно вызывать исключение
        try:
            validate_payment_status_transition('pending', 'paid')
        except ValidationError:
            self.fail("Valid payment status transition should not raise exception")


class ValidatorIntegrationTests(TestCase):
    """Интеграционные тесты валидаторов"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='USER'
        )
        
        self.order = Order.objects.create(
            user=self.user,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        self.payment = Payment.objects.create(
            order=self.order,
            amount=Decimal('100.00'),
            payment_system='stripe',
            status='pending'
        )
    
    def test_order_status_validation_in_model_save(self):
        """Тест валидации статуса заказа при сохранении модели"""
        # Изменяем статус на валидный
        self.order.status = 'processing'
        self.order.save()  # Не должно вызывать исключение
        
        # Изменяем статус на невалидный
        self.order.status = 'completed'
        self.order.status = 'pending'  # Невалидный переход
        
        with self.assertRaises(ValidationError):
            self.order.save()
    
    def test_payment_status_validation_in_model_save(self):
        """Тест валидации статуса платежа при сохранении модели"""
        # Изменяем статус на валидный
        self.payment.status = 'paid'
        self.payment.save()  # Не должно вызывать исключение
        
        # Изменяем статус на невалидный
        self.payment.status = 'failed'  # Невалидный переход от 'paid'
        
        with self.assertRaises(ValidationError):
            self.payment.save()
    
    def test_validator_error_messages(self):
        """Тест сообщений об ошибках валидаторов"""
        # Тест сообщения для заказа
        with self.assertRaises(ValidationError) as context:
            validate_order_status_transition('completed', 'pending')
        
        error_message = str(context.exception)
        self.assertIn('Недопустимый переход статуса с', error_message)
        self.assertIn('completed', error_message)
        self.assertIn('pending', error_message)
        
        # Тест сообщения для платежа
        with self.assertRaises(ValidationError) as context:
            validate_payment_status_transition('paid', 'failed')
        
        error_message = str(context.exception)
        self.assertIn('Недопустимый переход статуса платежа', error_message)
        self.assertIn('paid', error_message)
        self.assertIn('failed', error_message)
    
    def test_validator_with_none_values(self):
        """Тест валидаторов с None значениями"""
        with self.assertRaises(ValidationError):
            validate_order_status_transition(None, 'pending')
        
        with self.assertRaises(ValidationError):
            validate_order_status_transition('pending', None)
        
        with self.assertRaises(ValidationError):
            validate_payment_status_transition(None, 'paid')
        
        with self.assertRaises(ValidationError):
            validate_payment_status_transition('pending', None)
    
    def test_validator_with_empty_strings(self):
        """Тест валидаторов с пустыми строками"""
        with self.assertRaises(ValidationError):
            validate_order_status_transition('', 'pending')
        
        with self.assertRaises(ValidationError):
            validate_order_status_transition('pending', '')
        
        with self.assertRaises(ValidationError):
            validate_payment_status_transition('', 'paid')
        
        with self.assertRaises(ValidationError):
            validate_payment_status_transition('pending', '')
    
    def test_validator_performance(self):
        """Тест производительности валидаторов"""
        import time
        
        # Измеряем время выполнения множественных валидаций
        start_time = time.time()
        
        for _ in range(1000):
            validate_order_status_transition('pending', 'processing')
            validate_payment_status_transition('pending', 'paid')
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Валидация должна быть быстрой (менее 1 секунды для 1000 операций)
        self.assertLess(execution_time, 1.0)