"""
API тесты для приложения shop
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


class BaseAPITestCase(APITestCase):
    """Базовый класс для API тестов"""
    
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


class ProductAPITests(BaseAPITestCase):
    """Тесты API для продуктов"""
    
    def test_products_list_api(self):
        """Тест получения списка товаров"""
        url = reverse('api-product-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Тестовый товар')
        self.assertEqual(response.data[0]['price'], '100.00')
    
    def test_product_detail_api(self):
        """Тест получения детальной информации о товаре"""
        url = reverse('api-product-detail', kwargs={'pk': self.product.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Тестовый товар')
        self.assertEqual(response.data['price'], '100.00')
        self.assertEqual(response.data['category'], 'Электроника')
    
    def test_product_not_found(self):
        """Тест получения несуществующего товара"""
        url = reverse('api-product-detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_products_filter_by_category(self):
        """Тест фильтрации товаров по категории"""
        # Создаем вторую категорию и товар
        category2 = Category.objects.create(name='Одежда', slug='clothing')
        product2 = Product.objects.create(
            name='Футболка',
            slug='t-shirt',
            price=Decimal('50.00'),
            category=category2,
            available=True
        )
        
        url = reverse('api-product-list')
        response = self.client.get(url, {'category': self.category.slug})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Тестовый товар')


class CartAPITests(BaseAPITestCase):
    """Тесты API для корзины"""
    
    def test_cart_get(self):
        """Тест получения корзины"""
        url = reverse('api-cart')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('items', response.data)
        self.assertIn('total_price', response.data)
        self.assertEqual(response.data['total_price'], '0.00')
    
    def test_add_to_cart(self):
        """Тест добавления товара в корзину"""
        url = reverse('api-cart-add')
        data = {
            'product_id': self.product.id,
            'quantity': 2
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Проверяем что товар добавился в корзину
        cart_response = self.client.get(reverse('api-cart'))
        self.assertEqual(len(cart_response.data['items']), 1)
        self.assertEqual(cart_response.data['items'][0]['quantity'], 2)
        self.assertEqual(cart_response.data['total_price'], '200.00')
    
    def test_add_to_cart_invalid_product(self):
        """Тест добавления несуществующего товара"""
        url = reverse('api-cart-add')
        data = {
            'product_id': 99999,
            'quantity': 1
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_add_to_cart_invalid_quantity(self):
        """Тест добавления товара с неверным количеством"""
        url = reverse('api-cart-add')
        data = {
            'product_id': self.product.id,
            'quantity': -1
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_remove_from_cart(self):
        """Тест удаления товара из корзины"""
        # Сначала добавляем товар
        self.cart.add_product(self.product, 2)
        
        url = reverse('api-cart-item-detail', kwargs={'item_id': self.cart.items.first().id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Проверяем что корзина пустая
        cart_response = self.client.get(reverse('api-cart'))
        self.assertEqual(len(cart_response.data['items']), 0)
    
    def test_clear_cart(self):
        """Тест очистки корзины"""
        # Добавляем товар
        self.cart.add_product(self.product, 2)
        
        url = reverse('api-cart-clear')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем что корзина пустая
        cart_response = self.client.get(reverse('api-cart'))
        self.assertEqual(len(cart_response.data['items']), 0)


class OrderAPITests(BaseAPITestCase):
    """Тесты API для заказов"""
    
    def test_create_order(self):
        """Тест создания заказа"""
        # Добавляем товар в корзину
        self.cart.add_product(self.product, 2)
        
        url = reverse('order-list-create')
        data = {
            'email': 'test@example.com',
            'phone': '+380501234567',
            'address': 'Киев, ул. Тестовая, 1',
            'city': 'Киев',
            'delivery_method': 'nova_poshta',
            'delivery_type': 'prepaid'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['total_price'], '200.00')
    
    def test_create_order_invalid_data(self):
        """Тест создания заказа с неверными данными"""
        url = reverse('order-list-create')
        data = {
            'email': 'invalid-email',
            'phone': '123',
            'address': '',
            'city': ''
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_get_user_orders(self):
        """Тест получения заказов пользователя"""
        url = reverse('order-list-create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['email'], 'test@example.com')
    
    def test_get_order_detail(self):
        """Тест получения детальной информации о заказе"""
        url = reverse('order-detail', kwargs={'order_id': self.order.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        self.assertEqual(response.data['total_price'], '100.00')


class AuthenticationAPITests(BaseAPITestCase):
    """Тесты аутентификации"""
    
    def test_unauthorized_access(self):
        """Тест неавторизованного доступа"""
        # Убираем токен
        self.client.credentials()
        
        url = reverse('api-cart')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_invalid_token(self):
        """Тест неверного токена"""
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid-token')
        
        url = reverse('api-cart')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_registration(self):
        """Тест регистрации пользователя"""
        url = reverse('register')
        data = {
            'email': 'newuser@example.com',
            'password': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], 'newuser@example.com')
        
        # Проверяем что пользователь создался
        user = User.objects.get(email='newuser@example.com')
        self.assertEqual(user.first_name, 'New')
    
    def test_user_login(self):
        """Тест входа пользователя"""
        url = reverse('login')
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)


class NovaPoshtaAPITests(BaseAPITestCase):
    """Тесты API для Nova Poshta (отключены из-за проблем с DAL)"""
    
    def setUp(self):
        self.skipTest("Nova Poshta API тесты отключены из-за проблем с DAL")
    
    @patch('shop.views.requests.post')
    def test_get_cities(self, mock_post):
        """Тест получения городов"""
        # Настраиваем mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'data': [
                {
                    'Ref': 'city_ref_1',
                    'Description': 'Киев',
                    'AreaDescription': 'Киевская область'
                }
            ]
        }
        mock_post.return_value = mock_response
        
        url = reverse('np_get_cities')
        response = self.client.get(url, {'search': 'Киев'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['Description'], 'Киев')
    
    @patch('shop.views.requests.post')
    def test_get_warehouses(self, mock_post):
        """Тест получения отделений"""
        # Настраиваем mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True,
            'data': [
                {
                    'Ref': 'warehouse_ref_1',
                    'Description': 'Отделение №1',
                    'CityRef': 'city_ref_1'
                }
            ]
        }
        mock_post.return_value = mock_response
        
        url = reverse('np_get_warehouses')
        response = self.client.get(url, {'city_ref': 'city_ref_1'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        self.assertEqual(response.data['data'][0]['Description'], 'Отделение №1') 