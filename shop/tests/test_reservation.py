"""
Тесты для системы резервации товаров
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from ..models import (
    Order, Payment, Product, Category, Cart, CartItem, 
    ReservationSettings, OrderItem
)

User = get_user_model()


class ReservationSettingsTests(TestCase):
    """Тесты модели ReservationSettings"""
    
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
    
    def test_create_reservation_settings(self):
        """Тест создания настроек резервации"""
        settings = ReservationSettings.objects.create(
            is_enabled=True,
            reservation_time_minutes=60,
            auto_cancel_enabled=True,
            cleanup_interval_minutes=5
        )
        
        self.assertTrue(settings.is_enabled)
        self.assertEqual(settings.reservation_time_minutes, 60)
        self.assertTrue(settings.auto_cancel_enabled)
        self.assertEqual(settings.cleanup_interval_minutes, 5)
    
    def test_get_settings_creates_default(self):
        """Тест получения настроек с созданием по умолчанию"""
        # Убеждаемся, что настроек нет
        self.assertEqual(ReservationSettings.objects.count(), 0)
        
        # Получаем настройки (должны создаться автоматически)
        settings = ReservationSettings.get_settings()
        
        self.assertEqual(ReservationSettings.objects.count(), 1)
        self.assertTrue(settings.is_enabled)
        self.assertEqual(settings.reservation_time_minutes, 60)
        self.assertTrue(settings.auto_cancel_enabled)
        self.assertEqual(settings.cleanup_interval_minutes, 5)
    
    def test_get_settings_returns_existing(self):
        """Тест получения существующих настроек"""
        # Создаем настройки
        original_settings = ReservationSettings.objects.create(
            is_enabled=False,
            reservation_time_minutes=30,
            auto_cancel_enabled=False,
            cleanup_interval_minutes=10
        )
        
        # Получаем настройки
        settings = ReservationSettings.get_settings()
        
        self.assertEqual(settings.id, original_settings.id)
        self.assertFalse(settings.is_enabled)
        self.assertEqual(settings.reservation_time_minutes, 30)
        self.assertFalse(settings.auto_cancel_enabled)
        self.assertEqual(settings.cleanup_interval_minutes, 10)
    
    def test_unique_settings_constraint(self):
        """Тест ограничения уникальности настроек"""
        # Создаем первые настройки
        ReservationSettings.objects.create(
            is_enabled=True,
            reservation_time_minutes=60
        )
        
        # Пытаемся создать вторые настройки
        with self.assertRaises(ValidationError) as context:
            ReservationSettings.objects.create(
                is_enabled=False,
                reservation_time_minutes=30
            )
        
        self.assertIn("Можно создать только одну запись", str(context.exception))
    
    def test_str_representation(self):
        """Тест строкового представления"""
        settings = ReservationSettings.objects.create(
            is_enabled=True,
            reservation_time_minutes=60
        )
        
        self.assertIn("Включена", str(settings))
        self.assertIn("60", str(settings))
        
        settings.is_enabled = False
        settings.save()
        
        self.assertIn("Отключена", str(settings))


class OrderReservationTests(TestCase):
    """Тесты резервации заказов"""
    
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
        
        # Создаем настройки резервации
        self.settings = ReservationSettings.objects.create(
            is_enabled=True,
            reservation_time_minutes=60,
            auto_cancel_enabled=True,
            cleanup_interval_minutes=5
        )
    
    def test_set_reservation_time_enabled(self):
        """Тест установки времени резервации (включена)"""
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        order.set_reservation_time()
        
        self.assertIsNotNone(order.reserved_until)
        expected_time = timezone.now() + timedelta(minutes=60)
        # Проверяем, что время установлено примерно правильно (с погрешностью в 1 минуту)
        time_diff = abs((order.reserved_until - expected_time).total_seconds())
        self.assertLess(time_diff, 60)
    
    def test_set_reservation_time_disabled(self):
        """Тест установки времени резервации (отключена)"""
        # Отключаем резервацию
        self.settings.is_enabled = False
        self.settings.save()
        
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        order.set_reservation_time()
        
        self.assertIsNone(order.reserved_until)
    
    def test_is_reservation_expired(self):
        """Тест проверки истечения резерва"""
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        # Резерв не установлен
        self.assertFalse(order.is_reservation_expired())
        
        # Резерв в будущем
        order.reserved_until = timezone.now() + timedelta(minutes=30)
        order.save()
        self.assertFalse(order.is_reservation_expired())
        
        # Резерв в прошлом
        order.reserved_until = timezone.now() - timedelta(minutes=30)
        order.save()
        self.assertTrue(order.is_reservation_expired())
    
    def test_get_reservation_time_left(self):
        """Тест получения оставшегося времени резерва"""
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        # Резерв не установлен
        self.assertIsNone(order.get_reservation_time_left())
        
        # Резерв в будущем
        order.reserved_until = timezone.now() + timedelta(minutes=30)
        order.save()
        time_left = order.get_reservation_time_left()
        self.assertIsNotNone(time_left)
        self.assertGreater(time_left, 25)  # Примерно 30 минут
        self.assertLess(time_left, 35)
        
        # Резерв в прошлом
        order.reserved_until = timezone.now() - timedelta(minutes=30)
        order.save()
        self.assertEqual(order.get_reservation_time_left(), 0)
    
    def test_cancel_order(self):
        """Тест отмены заказа с возвратом товаров"""
        # Создаем заказ с товарами
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='pending'
        )
        
        # Создаем элемент заказа
        OrderItem.objects.create(
            order=order,
            product=self.product,
            quantity=2,
            price=self.product.price
        )
        
        # Уменьшаем остаток товара (имитируем резервацию)
        self.product.stock = 8
        self.product.save()
        
        # Отменяем заказ
        order.cancel_order()
        
        # Проверяем, что товар вернулся на склад
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)
        
        # Проверяем, что заказ отменен
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertIsNone(order.reserved_until)
    
    def test_cancel_already_cancelled_order(self):
        """Тест отмены уже отмененного заказа"""
        order = Order.objects.create(
            user=self.user,
            total_price=100.00,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            status='cancelled'
        )
        
        # Отмена уже отмененного заказа не должна вызывать ошибку
        order.cancel_order()
        
        # Статус должен остаться 'cancelled'
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')


class CartReservationTests(TestCase):
    """Тесты резервации в корзине"""
    
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
        
        self.cart = Cart.objects.create(user=self.user)
        
        # Создаем настройки резервации
        self.settings = ReservationSettings.objects.create(
            is_enabled=True,
            reservation_time_minutes=60,
            auto_cancel_enabled=True,
            cleanup_interval_minutes=5
        )
    
    def test_create_order_with_reservation_enabled(self):
        """Тест создания заказа с включенной резервацией"""
        # Добавляем товар в корзину
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Создаем заказ
        order = self.cart.create_order(
            shipping_address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев'
        )
        
        # Проверяем, что товар зарезервирован
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)  # 10 - 2 = 8
        
        # Проверяем, что заказ создан с резервом
        self.assertIsNotNone(order.reserved_until)
        expected_time = timezone.now() + timedelta(minutes=60)
        time_diff = abs((order.reserved_until - expected_time).total_seconds())
        self.assertLess(time_diff, 60)
    
    def test_create_order_with_reservation_disabled(self):
        """Тест создания заказа с отключенной резервацией"""
        # Отключаем резервацию
        self.settings.is_enabled = False
        self.settings.save()
        
        # Добавляем товар в корзину
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=2
        )
        
        # Создаем заказ
        order = self.cart.create_order(
            shipping_address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев'
        )
        
        # Проверяем, что товар НЕ зарезервирован
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)  # Остаток не изменился
        
        # Проверяем, что заказ создан без резерва
        self.assertIsNone(order.reserved_until)
    
    def test_create_order_insufficient_stock(self):
        """Тест создания заказа при недостаточном количестве товара"""
        # Добавляем больше товара, чем есть на складе
        CartItem.objects.create(
            cart=self.cart,
            product=self.product,
            quantity=15  # Больше чем stock=10
        )
        
        # Пытаемся создать заказ
        with self.assertRaises(ValidationError) as context:
            self.cart.create_order(
                shipping_address='Тестовый адрес',
                phone='+380501234567',
                email='test@example.com'
            )
        
        self.assertIn("Недостаточно товара", str(context.exception))
        
        # Проверяем, что товар не зарезервирован
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)  # Остаток не изменился
    
    def test_create_order_unavailable_product(self):
        """Тест создания заказа с недоступным товаром"""
        # Делаем товар недоступным
        self.product.available = False
        self.product.save()
        
        # Пытаемся добавить недоступный товар в корзину
        with self.assertRaises(ValidationError) as context:
            CartItem.objects.create(
                cart=self.cart,
                product=self.product,
                quantity=2
            )
        
        self.assertIn("недоступный товар", str(context.exception))
        
        # Проверяем, что товар не зарезервирован
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)  # Остаток не изменился


class ReservationIntegrationTests(TestCase):
    """Интеграционные тесты резервации"""
    
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
            stock=5  # Мало товара для тестирования
        )
        
        # Создаем настройки резервации
        self.settings = ReservationSettings.objects.create(
            is_enabled=True,
            reservation_time_minutes=60,
            auto_cancel_enabled=True,
            cleanup_interval_minutes=5
        )
    
    def test_multiple_users_competing_for_same_product(self):
        """Тест конкуренции нескольких пользователей за один товар"""
        # Создаем второго пользователя
        user2 = User.objects.create_user(
            email='test2@example.com',
            password='testpass123'
        )
        
        # Создаем корзины для обоих пользователей
        cart1 = Cart.objects.create(user=self.user)
        cart2 = Cart.objects.create(user=user2)
        
        # Оба пользователя добавляют товар в корзину
        CartItem.objects.create(cart=cart1, product=self.product, quantity=3)
        CartItem.objects.create(cart=cart2, product=self.product, quantity=3)
        
        # Первый пользователь создает заказ
        order1 = cart1.create_order(
            shipping_address='Адрес 1',
            phone='+380501234567',
            email='test@example.com',
            city='Киев'
        )
        
        # Проверяем, что товар зарезервирован
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)  # 5 - 3 = 2
        
        # Второй пользователь пытается создать заказ
        with self.assertRaises(ValidationError) as context:
            cart2.create_order(
                shipping_address='Адрес 2',
                phone='+380501234568',
                email='test2@example.com',
                city='Львов'
            )
        
        self.assertIn("Недостаточно товара", str(context.exception))
        
        # Проверяем, что остаток не изменился
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
    
    def test_reservation_expiration_and_cancellation(self):
        """Тест истечения резерва и отмены заказа"""
        cart = Cart.objects.create(user=self.user)
        CartItem.objects.create(cart=cart, product=self.product, quantity=2)
        
        # Создаем заказ
        order = cart.create_order(
            shipping_address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев'
        )
        
        # Проверяем резервацию
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 3)  # 5 - 2 = 3
        self.assertIsNotNone(order.reserved_until)
        
        # Имитируем истечение резерва
        order.reserved_until = timezone.now() - timedelta(minutes=1)
        order.save()
        
        # Отменяем заказ
        order.cancel_order()
        
        # Проверяем, что товар вернулся на склад
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)  # Вернулся к исходному количеству
        
        # Проверяем статус заказа
        order.refresh_from_db()
        self.assertEqual(order.status, 'cancelled')
        self.assertIsNone(order.reserved_until)