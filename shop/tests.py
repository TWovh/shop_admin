from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class SecurityTests(TestCase):
    def test_admin_access(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # Редирект на логин


class APITests(TestCase):
    def test_cart_throttling(self):
        for _ in range(100):
            self.client.post('/cart/add/', data={...})
        response = self.client.post('/cart/add/', data={...})
        self.assertEqual(response.status_code, 429)  # Too Many Requests


class ProductTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_product_creation(self):
        data = {'name': 'Test', 'price': 10, 'category': 1}
        response = self.client.post(reverse('product-list'), data)
        self.assertEqual(response.status_code, 201)

    def test_unauthorized_access(self):
        response = self.client.get(reverse('order-list'))
        self.assertEqual(response.status_code, 401)