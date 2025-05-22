from django.test import TestCase
from django.test.client import Client

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