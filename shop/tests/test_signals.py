"""
Тесты для Django signals
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, post_delete
from unittest.mock import patch

from shop.models import Order, OrderItem, Product, Category
from shop.signals import update_order_total_on_save, update_order_total_on_delete

User = get_user_model()


class OrderSignalsTests(TestCase):
    """Тесты для сигналов Order"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='USER'
        )
        
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category'
        )
        
        self.product1 = Product.objects.create(
            name='Товар 1',
            slug='product-1',
            category=self.category,
            price=Decimal('100.00'),
            stock=10,
            available=True
        )
        
        self.product2 = Product.objects.create(
            name='Товар 2',
            slug='product-2',
            category=self.category,
            price=Decimal('200.00'),
            stock=5,
            available=True
        )
        
        self.order = Order.objects.create(
            user=self.user,
            address='Тестовый адрес',
            phone='+380501234567',
            email='test@example.com',
            city='Киев',
            total_price=Decimal('0.00')
        )
    
    def test_order_total_update_on_item_save(self):
        """Тест обновления общей суммы заказа при сохранении элемента"""
        # Создаем элемент заказа
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=2,
            price=self.product1.price
        )
        
        # Проверяем, что общая сумма обновилась
        self.order.refresh_from_db()
        expected_total = self.product1.price * 2
        self.assertEqual(self.order.total_price, expected_total)
    
    def test_order_total_update_on_item_quantity_change(self):
        """Тест обновления общей суммы при изменении количества"""
        # Создаем элемент заказа
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=2,
            price=self.product1.price
        )
        
        # Изменяем количество
        order_item.quantity = 3
        order_item.save()
        
        # Проверяем обновленную сумму
        self.order.refresh_from_db()
        expected_total = self.product1.price * 3
        self.assertEqual(self.order.total_price, expected_total)
    
    def test_order_total_update_on_item_price_change(self):
        """Тест обновления общей суммы при изменении цены"""
        # Создаем элемент заказа
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=2,
            price=self.product1.price
        )
        
        # Изменяем цену
        new_price = Decimal('150.00')
        order_item.price = new_price
        order_item.save()
        
        # Проверяем обновленную сумму
        self.order.refresh_from_db()
        expected_total = new_price * 2
        self.assertEqual(self.order.total_price, expected_total)
    
    def test_order_total_update_on_multiple_items(self):
        """Тест обновления общей суммы при нескольких элементах"""
        # Создаем несколько элементов заказа
        OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=2,
            price=self.product1.price
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product2,
            quantity=1,
            price=self.product2.price
        )
        
        # Проверяем общую сумму
        self.order.refresh_from_db()
        expected_total = (self.product1.price * 2) + (self.product2.price * 1)
        self.assertEqual(self.order.total_price, expected_total)
    
    def test_order_total_update_on_item_delete(self):
        """Тест обновления общей суммы при удалении элемента"""
        # Создаем несколько элементов заказа
        item1 = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=2,
            price=self.product1.price
        )
        
        item2 = OrderItem.objects.create(
            order=self.order,
            product=self.product2,
            quantity=1,
            price=self.product2.price
        )
        
        # Удаляем один элемент
        item1.delete()
        
        # Проверяем, что сумма обновилась
        self.order.refresh_from_db()
        expected_total = self.product2.price * 1
        self.assertEqual(self.order.total_price, expected_total)
    
    def test_order_total_update_on_all_items_delete(self):
        """Тест обновления общей суммы при удалении всех элементов"""
        # Создаем элемент заказа
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=2,
            price=self.product1.price
        )
        
        # Удаляем элемент
        order_item.delete()
        
        # Проверяем, что сумма стала 0
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_price, Decimal('0.00'))
    
    def test_signal_connection(self):
        """Тест подключения сигналов"""
        # Проверяем, что сигналы подключены
        self.assertTrue(post_save.has_listeners(OrderItem))
        self.assertTrue(post_delete.has_listeners(OrderItem))
    
    def test_signal_handler_functions(self):
        """Тест функций-обработчиков сигналов"""
        # Проверяем, что функции существуют
        self.assertIsNotNone(update_order_total_on_save)
        self.assertIsNotNone(update_order_total_on_delete)
        
        # Проверяем, что это функции
        self.assertTrue(callable(update_order_total_on_save))
        self.assertTrue(callable(update_order_total_on_delete))
    
    def test_order_total_calculation_accuracy(self):
        """Тест точности расчета общей суммы"""
        # Создаем элементы с разными ценами и количествами
        OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=3,
            price=Decimal('99.99')
        )
        
        OrderItem.objects.create(
            order=self.order,
            product=self.product2,
            quantity=2,
            price=Decimal('149.50')
        )
        
        # Проверяем точность расчета
        self.order.refresh_from_db()
        expected_total = (Decimal('99.99') * 3) + (Decimal('149.50') * 2)
        self.assertEqual(self.order.total_price, expected_total)
    
    def test_signal_with_zero_quantity(self):
        """Тест сигнала с нулевым количеством"""
        # Создаем элемент с нулевым количеством
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=0,
            price=self.product1.price
        )
        
        # Проверяем, что сумма 0
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_price, Decimal('0.00'))
    
    def test_signal_with_zero_price(self):
        """Тест сигнала с нулевой ценой"""
        # Создаем элемент с нулевой ценой
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=2,
            price=Decimal('0.00')
        )
        
        # Проверяем, что сумма 0
        self.order.refresh_from_db()
        self.assertEqual(self.order.total_price, Decimal('0.00'))
    
    def test_signal_performance(self):
        """Тест производительности сигналов"""
        import time
        
        # Измеряем время создания множества элементов
        start_time = time.time()
        
        for i in range(10):
            OrderItem.objects.create(
                order=self.order,
                product=self.product1,
                quantity=1,
                price=self.product1.price
            )
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Проверяем, что время выполнения разумное (менее 1 секунды)
        self.assertLess(execution_time, 1.0)
        
        # Проверяем, что общая сумма корректна
        self.order.refresh_from_db()
        expected_total = self.product1.price * 10
        self.assertEqual(self.order.total_price, expected_total)
    
    def test_signal_with_mocked_update_total_price(self):
        """Тест сигнала с мокированным методом update_total_price"""
        with patch.object(Order, 'update_total_price') as mock_update:
            # Создаем элемент заказа
            OrderItem.objects.create(
                order=self.order,
                product=self.product1,
                quantity=2,
                price=self.product1.price
            )
            
            # Проверяем, что метод был вызван
            mock_update.assert_called_once()
    
    def test_signal_error_handling(self):
        """Тест обработки ошибок в сигналах"""
        # Создаем элемент заказа
        order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product1,
            quantity=2,
            price=self.product1.price
        )
        
        # Мокируем метод update_total_price, чтобы он выбрасывал исключение
        with patch.object(Order, 'update_total_price', side_effect=Exception("Test error")):
            # Попытка изменить элемент должна вызвать исключение
            with self.assertRaises(Exception):
                order_item.quantity = 3
                order_item.save()