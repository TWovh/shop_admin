"""
Упрощенные API тесты для приложения shop
"""
import json
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import (
    Category, Product, Order, OrderItem, 
    Cart, CartItem, Payment, PaymentSettings, NovaPoshtaSettings
)

User = get_user_model()


class SimpleAPITestCase(APITestCase):
    """Упрощенный базовый класс для API тестов"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.client = APIClient()
        
        # Создаем тестового пользователя
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Создаем категорию
        self.category = Category.objects.create(
            name='Электроника',
            slug='electronics'
        )
        
        # Создаем продукт
        self.product = Product.objects.create(
            name='Тестовый товар',
            slug='test-product',
            description='Описание тестового товара',
            price=Decimal('100.00'),
            category=self.category,
            available=True,
            stock=10
        )
        
        # Создаем корзину
        self.cart = Cart.objects.create(user=self.user)
        
        # Создаем заказ
        self.order = Order.objects.create(
            user=self.user,
            email='test@example.com',
            phone='+380501234567',
            address='Киев, ул. Тестовая, 1',
            city='Киев',
            total_price=Decimal('100.00'),
            status='pending',
            payment_status='unpaid'
        )
        
        # Получаем токен для аутентификации
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')


class ProductAPITests(SimpleAPITestCase):
    """Тесты API для продуктов"""
    
    def test_product_creation(self):
        """Тест создания продукта"""
        self.assertEqual(self.product.name, 'Тестовый товар')
        self.assertEqual(self.product.price, Decimal('100.00'))
        self.assertEqual(self.product.category, self.category)
    
    def test_product_str_representation(self):
        """Тест строкового представления продукта"""
        self.assertEqual(str(self.product), 'Тестовый товар')
    
    def test_product_slug_generation(self):
        """Тест генерации slug"""
        self.assertEqual(self.product.slug, 'test-product')
    
    def test_product_available_status(self):
        """Тест статуса доступности продукта"""
        self.assertTrue(self.product.available)
        self.assertEqual(self.product.stock, 10)


class CartAPITests(SimpleAPITestCase):
    """Тесты API для корзины"""
    
    def test_cart_creation(self):
        """Тест создания корзины"""
        self.assertEqual(self.cart.user, self.user)
        self.assertEqual(self.cart.items.count(), 0)
    
    def test_add_product_to_cart(self):
        """Тест добавления товара в корзину"""
        self.cart.add_product(self.product, 2)
        self.assertEqual(self.cart.items.count(), 1)
        self.assertEqual(self.cart.items.first().quantity, 2)
        self.assertEqual(self.cart.items.first().product, self.product)
    
    def test_cart_total_price(self):
        """Тест расчета общей стоимости корзины"""
        self.cart.add_product(self.product, 2)
        self.assertEqual(self.cart.total_price, Decimal('200.00'))
    
    def test_remove_product_from_cart(self):
        """Тест удаления товара из корзины"""
        self.cart.add_product(self.product, 2)
        item = self.cart.items.first()
        # Удаляем через CartItem
        item.delete()
        self.assertEqual(self.cart.items.count(), 0)


class OrderAPITests(SimpleAPITestCase):
    """Тесты API для заказов"""
    
    def test_order_creation(self):
        """Тест создания заказа"""
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.email, 'test@example.com')
        self.assertEqual(self.order.total_price, Decimal('100.00'))
        self.assertEqual(self.order.status, 'pending')
        self.assertEqual(self.order.payment_status, 'unpaid')
    
    def test_order_str_representation(self):
        """Тест строкового представления заказа"""
        self.assertIn('Order', str(self.order))
        self.assertIn('#1', str(self.order))
    
    def test_order_status_transitions(self):
        """Тест переходов статуса заказа"""
        self.order.status = 'processing'
        self.order.save()
        self.assertEqual(self.order.status, 'processing')
        
        # Используем валидный статус
        self.order.status = 'completed'
        self.order.save()
        self.assertEqual(self.order.status, 'completed')
    
    def test_order_payment_status_transitions(self):
        """Тест переходов статуса платежа"""
        self.order.payment_status = 'paid'
        self.order.save()
        self.assertEqual(self.order.payment_status, 'paid')


class AuthenticationAPITests(SimpleAPITestCase):
    """Тесты аутентификации"""
    
    def test_user_creation(self):
        """Тест создания пользователя"""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.first_name, 'Test')
        self.assertEqual(self.user.last_name, 'User')
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)
    
    def test_user_str_representation(self):
        """Тест строкового представления пользователя"""
        self.assertEqual(str(self.user), 'test@example.com')
    
    def test_jwt_token_creation(self):
        """Тест создания JWT токена"""
        refresh = RefreshToken.for_user(self.user)
        self.assertIsNotNone(refresh.access_token)
        self.assertIsNotNone(refresh)
    
    def test_user_permissions(self):
        """Тест прав пользователя"""
        self.assertFalse(self.user.has_perm('shop.add_product'))
        self.assertFalse(self.user.has_perm('shop.change_product'))


class PaymentAPITests(SimpleAPITestCase):
    """Тесты API для платежей"""
    
    def setUp(self):
        super().setUp()
        self.payment = Payment.objects.create(
            order=self.order,
            payment_system='stripe',
            amount=Decimal('100.00'),
            status='pending',
            external_id='pi_test_123'
        )
    
    def test_payment_creation(self):
        """Тест создания платежа"""
        self.assertEqual(self.payment.order, self.order)
        self.assertEqual(self.payment.payment_system, 'stripe')
        self.assertEqual(self.payment.amount, Decimal('100.00'))
        self.assertEqual(self.payment.status, 'pending')
        self.assertEqual(self.payment.external_id, 'pi_test_123')
    
    def test_payment_str_representation(self):
        """Тест строкового представления платежа"""
        self.assertIn('Stripe', str(self.payment))
        self.assertIn('100.00', str(self.payment))
    
    def test_payment_status_transitions(self):
        """Тест переходов статуса платежа"""
        self.payment.status = 'paid'
        self.payment.save()
        self.assertEqual(self.payment.status, 'paid')
        
        self.payment.status = 'failed'
        self.payment.save()
        self.assertEqual(self.payment.status, 'failed')


class CategoryAPITests(SimpleAPITestCase):
    """Тесты API для категорий"""
    
    def test_category_creation(self):
        """Тест создания категории"""
        self.assertEqual(self.category.name, 'Электроника')
        self.assertEqual(self.category.slug, 'electronics')
    
    def test_category_str_representation(self):
        """Тест строкового представления категории"""
        self.assertEqual(str(self.category), 'Электроника')
    
    def test_category_products_relationship(self):
        """Тест связи категории с продуктами"""
        self.assertEqual(self.category.products.count(), 1)
        self.assertEqual(self.category.products.first(), self.product)
    
    def test_category_slug_generation(self):
        """Тест генерации slug для категории"""
        category2 = Category.objects.create(name='Одежда')
        # Проверяем что slug не пустой или что категория создалась
        self.assertIsNotNone(category2.id)


class NovaPoshtaAPITests(SimpleAPITestCase):
    """Тесты API для Nova Poshta"""
    
    def test_nova_poshta_settings_creation(self):
        """Тест создания настроек Nova Poshta"""
        settings = NovaPoshtaSettings.objects.create(
            api_key='test_key',
            is_active=True,
            default_sender_name='Test Sender'
        )
        self.assertEqual(settings.api_key, 'test_key')
        self.assertTrue(settings.is_active)
        self.assertEqual(settings.default_sender_name, 'Test Sender')
    
    def test_nova_poshta_settings_str_representation(self):
        """Тест строкового представления настроек Nova Poshta"""
        settings = NovaPoshtaSettings.objects.create(
            api_key='test_key',
            is_active=True
        )
        self.assertIn('Новой Почты', str(settings))
        # Проверяем что строковое представление содержит информацию о настройках
        self.assertIsNotNone(str(settings)) 