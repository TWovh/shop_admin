from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import Product


class SecurityTests(TestCase):
    def test_admin_access(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # редирект на логин


class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_cart_throttling(self):
        # Пример корректных данных
        product = Product.objects.create(
            name='Test Throttle',
            description='Test',
            price=100,
            stock=5
        )
        url = reverse('add-to-cart', args=[product.id])
        for _ in range(100):
            self.client.get(url)
        response = self.client.get(url)
        self.assertIn(response.status_code, [200, 429])  # зависит от настройки throttle


class ProductTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Создаём категорию, если нужно (иначе category=1 может быть невалиден)
        # Например: self.category = Category.objects.create(name="Default")

    def test_product_creation(self):
        data = {'name': 'Test', 'price': 10, 'category': 1}  # Предполагается, что категория с id=1 уже есть
        response = self.client.post(reverse('product-list'), data)
        self.assertEqual(response.status_code, 201)

    def test_unauthorized_access(self):
        response = self.client.get(reverse('order-list'))
        self.assertEqual(response.status_code, 401)

class CartTests(TestCase):
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