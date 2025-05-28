from rest_framework.test import APIClient
from .models import Product
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken


class SecurityTests(APITestCase):
    def test_admin_access(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # редирект на логин


class APITests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(
            name='Test Throttle',
            description='For throttling test',
            price=10,
            stock=5
        )

    def test_cart_throttling(self):
        data = {'product_id': self.product.id, 'quantity': 1}
        for _ in range(100):
            self.client.post('/cart/add/', data=data)
        response = self.client.post('/cart/add/', data=data)
        self.assertEqual(response.status_code, 429)  # зависит от настройки throttle


class ProductTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='admin123')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')

    def test_product_creation(self):
        url = reverse('product-list')  # убедись, что такой name есть
        data = {
            'name': 'New Product',
            'price': 9.99,
            'stock': 10
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

class CartTests(APITestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Test Product',
            description='Test description',
            price=50.00,
            stock=10
        )

    def test_add_to_cart_success(self):
        response = self.client.get(reverse('add-to-cart', args=[self.product.id]))
        self.assertEqual(response.status_code, 302)

        session = self.client.session
        cart = session.get('cart', {})
        self.assertIn(str(self.product.id), cart)
        self.assertEqual(cart[str(self.product.id)], 1)

    def test_add_non_existing_product(self):
        response = self.client.get(reverse('add-to-cart', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_adding_same_product_twice_increments_quantity(self):
        url = reverse('add-to-cart', args=[self.product.id])
        self.client.get(url)
        self.client.get(url)

        session = self.client.session
        cart = session.get('cart', {})
        self.assertEqual(cart[str(self.product.id)], 2)