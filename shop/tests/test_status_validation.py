"""
Тесты для валидации переходов статусов заказов и платежей
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from ..models import Order, Payment, Product, Category
from ..validators import validate_order_status_transition, validate_payment_status_transition

User = get_user_model()


class OrderStatusValidationTests(TestCase):
    """Тесты валидации переходов статусов заказов"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Тестовый товар',
            slug='test-product',
            price=100.00,
            stock=10
        )
        
        self.order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
    
    def test_valid_status_transitions(self):
        """Тест корректных переходов статусов заказов"""
        # pending -> processing
        self.order.status = 'processing'
        self.order.save()  # Не должно вызывать ошибку
        
        # processing -> completed
        self.order.status = 'completed'
        self.order.save()  # Не должно вызывать ошибку
        
        # Создаем новый заказ для тестирования других переходов
        order2 = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        # pending -> cancelled
        order2.status = 'cancelled'
        order2.save()  # Не должно вызывать ошибку
    
    def test_invalid_status_transitions(self):
        """Тест некорректных переходов статусов заказов"""
        # pending -> completed (недопустимо)
        with self.assertRaises(ValidationError) as context:
            self.order.status = 'completed'
            self.order.save()
        
        self.assertIn('Недопустимый переход статуса', str(context.exception))
        
        # Создаем заказ в статусе processing для дальнейших тестов
        order_processing = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        order_processing.status = 'processing'
        order_processing.save()
        
        # completed -> pending (недопустимо)
        order_processing.status = 'completed'
        order_processing.save()
        
        with self.assertRaises(ValidationError) as context:
            order_processing.status = 'pending'
            order_processing.save()
        
        self.assertIn('Недопустимый переход статуса', str(context.exception))
        
        # completed -> processing (недопустимо)
        with self.assertRaises(ValidationError) as context:
            order_processing.status = 'processing'
            order_processing.save()
        
        self.assertIn('Недопустимый переход статуса', str(context.exception))
        
        # cancelled -> processing (недопустимо)
        order2 = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        order2.status = 'cancelled'
        order2.save()
        
        with self.assertRaises(ValidationError) as context:
            order2.status = 'processing'
            order2.save()
        
        self.assertIn('Недопустимый переход статуса', str(context.exception))
    
    def test_same_status_no_validation_error(self):
        """Тест что сохранение с тем же статусом не вызывает ошибку"""
        # Сохраняем заказ с тем же статусом
        self.order.status = 'pending'
        self.order.save()  # Не должно вызывать ошибку
        
        # Проверяем что статус не изменился
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'pending')
    
    def test_new_order_creation_no_validation_error(self):
        """Тест что создание нового заказа не вызывает ошибку валидации"""
        # Создаем новый заказ
        new_order = Order.objects.create(
            user=self.user,
            total_price=200.00,
            address='Новый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='processing'  # Любой статус при создании допустим
        )
        
        # Проверяем что заказ создался
        self.assertEqual(new_order.status, 'processing')
    
    def test_validator_function_directly(self):
        """Тест валидатора напрямую"""
        # Корректные переходы
        validate_order_status_transition('pending', 'processing')
        validate_order_status_transition('pending', 'cancelled')
        validate_order_status_transition('processing', 'completed')
        validate_order_status_transition('processing', 'cancelled')
        
        # Некорректные переходы
        with self.assertRaises(ValidationError):
            validate_order_status_transition('completed', 'pending')
        
        with self.assertRaises(ValidationError):
            validate_order_status_transition('cancelled', 'processing')
        
        with self.assertRaises(ValidationError):
            validate_order_status_transition('completed', 'processing')


class PaymentStatusValidationTests(TestCase):
    """Тесты валидации переходов статусов платежей"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Тестовый товар',
            slug='test-product',
            price=100.00,
            stock=10
        )
        
        self.order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        self.payment = Payment.objects.create(
            order=self.order,
            amount=100.00,
            status='pending',
            payment_system='stripe'
        )
    
    def test_valid_payment_status_transitions(self):
        """Тест корректных переходов статусов платежей"""
        # pending -> paid
        self.payment.status = 'paid'
        self.payment.save()  # Не должно вызывать ошибку
        
        # Создаем новый платеж для тестирования других переходов
        payment2 = Payment.objects.create(
            order=self.order,
            amount=100.00,
            status='pending',
            payment_system='paypal'
        )
        
        # pending -> failed
        payment2.status = 'failed'
        payment2.save()  # Не должно вызывать ошибку
        
        # failed -> pending (повторная попытка)
        payment2.status = 'pending'
        payment2.save()  # Не должно вызывать ошибку
        
        # paid -> refunded
        payment3 = Payment.objects.create(
            order=self.order,
            amount=100.00,
            status='paid',
            payment_system='stripe'
        )
        payment3.status = 'refunded'
        payment3.save()  # Не должно вызывать ошибку
    
    def test_invalid_payment_status_transitions(self):
        """Тест некорректных переходов статусов платежей"""
        # paid -> pending (недопустимо)
        self.payment.status = 'paid'
        self.payment.save()
        
        with self.assertRaises(ValidationError) as context:
            self.payment.status = 'pending'
            self.payment.save()
        
        self.assertIn('Недопустимый переход статуса платежа', str(context.exception))
        
        # paid -> failed (недопустимо)
        with self.assertRaises(ValidationError) as context:
            self.payment.status = 'failed'
            self.payment.save()
        
        self.assertIn('Недопустимый переход статуса платежа', str(context.exception))
        
        # refunded -> paid (недопустимо)
        payment2 = Payment.objects.create(
            order=self.order,
            amount=100.00,
            status='paid',
            payment_system='stripe'
        )
        payment2.status = 'refunded'
        payment2.save()
        
        with self.assertRaises(ValidationError) as context:
            payment2.status = 'paid'
            payment2.save()
        
        self.assertIn('Недопустимый переход статуса платежа', str(context.exception))
    
    def test_same_payment_status_no_validation_error(self):
        """Тест что сохранение с тем же статусом не вызывает ошибку"""
        # Сохраняем платеж с тем же статусом
        self.payment.status = 'pending'
        self.payment.save()  # Не должно вызывать ошибку
        
        # Проверяем что статус не изменился
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')
    
    def test_new_payment_creation_no_validation_error(self):
        """Тест что создание нового платежа не вызывает ошибку валидации"""
        # Создаем новый платеж
        new_payment = Payment.objects.create(
            order=self.order,
            amount=200.00,
            status='paid',  # Любой статус при создании допустим
            payment_system='stripe'
        )
        
        # Проверяем что платеж создался
        self.assertEqual(new_payment.status, 'paid')
    
    def test_payment_validator_function_directly(self):
        """Тест валидатора платежей напрямую"""
        # Корректные переходы
        validate_payment_status_transition('pending', 'paid')
        validate_payment_status_transition('pending', 'failed')
        validate_payment_status_transition('failed', 'pending')
        validate_payment_status_transition('paid', 'refunded')
        
        # Некорректные переходы
        with self.assertRaises(ValidationError):
            validate_payment_status_transition('paid', 'pending')
        
        with self.assertRaises(ValidationError):
            validate_payment_status_transition('refunded', 'paid')
        
        with self.assertRaises(ValidationError):
            validate_payment_status_transition('paid', 'failed')


class StatusValidationIntegrationTests(TestCase):
    """Интеграционные тесты валидации статусов"""
    
    def setUp(self):
        """Подготовка тестовых данных"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            category=self.category,
            name='Тестовый товар',
            slug='test-product',
            price=100.00,
            stock=10
        )
    
    def test_order_and_payment_status_consistency(self):
        """Тест согласованности статусов заказа и платежа"""
        # Создаем заказ
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        # Создаем платеж
        payment = Payment.objects.create(
            order=order,
            amount=100.00,
            status='pending',
            payment_system='stripe'
        )
        
        # Платеж успешен - заказ должен перейти в processing
        payment.status = 'paid'
        payment.save()
        
        # В реальном приложении здесь должна быть логика обновления статуса заказа
        # Но для теста просто проверяем что платеж сохранился
        payment.refresh_from_db()
        self.assertEqual(payment.status, 'paid')
    
    def test_multiple_payments_same_order(self):
        """Тест множественных платежей для одного заказа"""
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        # Первый платеж - неудачный
        payment1 = Payment.objects.create(
            order=order,
            amount=100.00,
            status='pending',
            payment_system='stripe'
        )
        payment1.status = 'failed'
        payment1.save()
        
        # Второй платеж - успешный
        payment2 = Payment.objects.create(
            order=order,
            amount=100.00,
            status='pending',
            payment_system='paypal'
        )
        payment2.status = 'paid'
        payment2.save()
        
        # Проверяем что оба платежа сохранились с правильными статусами
        payment1.refresh_from_db()
        payment2.refresh_from_db()
        
        self.assertEqual(payment1.status, 'failed')
        self.assertEqual(payment2.status, 'paid')