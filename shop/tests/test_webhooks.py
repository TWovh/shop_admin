"""
Тесты webhook'ов платежных систем
"""
import json
import hashlib
import hmac
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from ..models import (
    Category, Product, Order, OrderItem, 
    Cart, CartItem, Payment, PaymentSettings, NovaPoshtaSettings
)

User = get_user_model()


class WebhookTestCase(TestCase):
    """Базовый класс для тестов webhook'ов"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.client = Client()
        
        # Создаем тестового пользователя
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Создаем категорию и продукт
        self.category = Category.objects.create(
            name='Электроника',
            slug='electronics'
        )
        
        self.product = Product.objects.create(
            name='Тестовый товар',
            slug='test-product',
            description='Описание тестового товара',
            price=Decimal('100.00'),
            category=self.category,
            available=True,
            stock=10
        )
        
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
        
        # Создаем платеж
        self.payment = Payment.objects.create(
            order=self.order,
            payment_system='stripe',
            amount=Decimal('100.00'),
            status='pending',
            external_id='pi_test_123'
        )


class StripeWebhookTests(WebhookTestCase):
    """Тесты webhook'ов Stripe"""
    
    def test_stripe_webhook_success(self):
        """Тест успешного webhook'а Stripe"""
        # Данные webhook'а
        webhook_data = {
            'id': 'evt_test_123',
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_test_123',
                    'amount': 10000,  # в центах
                    'status': 'succeeded',
                    'metadata': {
                        'order_id': str(self.order.id)
                    }
                }
            }
        }
        
        # Создаем подпись
        payload = json.dumps(webhook_data).encode('utf-8')
        signature = f"t={int(1234567890)},v1={hmac.new(b'whsec_test_secret', payload, hashlib.sha256).hexdigest()}"
        
        # Отправляем webhook
        response = self.client.post(
            reverse('stripe-webhook'),
            data=payload,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем что платеж обновился
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')
        
        # Проверяем что заказ обновился
        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_status, 'paid')
    
    def test_stripe_webhook_invalid_signature(self):
        """Тест webhook'а с неверной подписью"""
        webhook_data = {
            'id': 'evt_test_123',
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_test_123',
                    'amount': 10000,
                    'status': 'succeeded'
                }
            }
        }
        
        payload = json.dumps(webhook_data).encode('utf-8')
        invalid_signature = "t=1234567890,v1=invalid_signature"
        
        response = self.client.post(
            reverse('stripe-webhook'),
            data=payload,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE=invalid_signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_stripe_webhook_payment_failed(self):
        """Тест webhook'а о неудачном платеже"""
        webhook_data = {
            'id': 'evt_test_123',
            'type': 'payment_intent.payment_failed',
            'data': {
                'object': {
                    'id': 'pi_test_123',
                    'amount': 10000,
                    'status': 'requires_payment_method'
                }
            }
        }
        
        payload = json.dumps(webhook_data).encode('utf-8')
        signature = f"t={int(1234567890)},v1={hmac.new(b'whsec_test_secret', payload, hashlib.sha256).hexdigest()}"
        
        response = self.client.post(
            reverse('stripe-webhook'),
            data=payload,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем что платеж обновился
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')


class PayPalWebhookTests(WebhookTestCase):
    """Тесты webhook'ов PayPal"""
    
    def test_paypal_webhook_payment_completed(self):
        """Тест webhook'а о завершенном платеже PayPal"""
        webhook_data = {
            'id': 'WH-1234567890',
            'event_type': 'PAYMENT.CAPTURE.COMPLETED',
            'resource': {
                'id': 'capture_123',
                'status': 'COMPLETED',
                'amount': {
                    'currency_code': 'USD',
                    'value': '100.00'
                },
                'custom_id': str(self.order.id)
            }
        }
        
        response = self.client.post(
            reverse('paypal-webhook'),
            data=webhook_data,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем что платеж обновился
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')
    
    def test_paypal_webhook_payment_denied(self):
        """Тест webhook'а об отклоненном платеже PayPal"""
        webhook_data = {
            'id': 'WH-1234567890',
            'event_type': 'PAYMENT.CAPTURE.DENIED',
            'resource': {
                'id': 'capture_123',
                'status': 'DENIED',
                'custom_id': str(self.order.id)
            }
        }
        
        response = self.client.post(
            reverse('paypal-webhook'),
            data=webhook_data,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем что платеж обновился
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')


class FondyWebhookTests(WebhookTestCase):
    """Тесты webhook'ов Fondy"""
    
    def test_fondy_webhook_success(self):
        """Тест успешного webhook'а Fondy"""
        webhook_data = {
            'order_id': str(self.order.id),
            'payment_id': 'fondy_payment_123',
            'status': 'approved',
            'amount': 10000,  # в копейках
            'currency': 'UAH'
        }
        
        # Создаем подпись
        signature_data = '|'.join([
            webhook_data['order_id'],
            webhook_data['payment_id'],
            webhook_data['status'],
            str(webhook_data['amount']),
            webhook_data['currency']
        ])
        signature = hmac.new(
            b'fondy_secret_key',
            signature_data.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        
        response = self.client.post(
            reverse('fondy-webhook'),
            data=webhook_data,
            content_type='application/json',
            HTTP_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем что платеж обновился
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')


class LiqPayWebhookTests(WebhookTestCase):
    """Тесты webhook'ов LiqPay"""
    
    def test_liqpay_webhook_success(self):
        """Тест успешного webhook'а LiqPay"""
        webhook_data = {
            'order_id': str(self.order.id),
            'payment_id': 'liqpay_payment_123',
            'status': 'success',
            'amount': 100.00,
            'currency': 'UAH',
            'transaction_id': 'txn_123'
        }
        
        # Создаем подпись
        signature_data = '|'.join([
            webhook_data['order_id'],
            webhook_data['payment_id'],
            webhook_data['status'],
            str(webhook_data['amount']),
            webhook_data['currency']
        ])
        signature = hmac.new(
            b'liqpay_secret_key',
            signature_data.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        
        response = self.client.post(
            reverse('liqpay-webhook'),
            data=webhook_data,
            content_type='application/json',
            HTTP_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем что платеж обновился
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')


class PortmoneWebhookTests(WebhookTestCase):
    """Тесты webhook'ов Portmone"""
    
    def test_portmone_webhook_success(self):
        """Тест успешного webhook'а Portmone"""
        webhook_data = {
            'order_id': str(self.order.id),
            'payment_id': 'portmone_payment_123',
            'status': 'PAID',
            'amount': 100.00,
            'currency': 'UAH'
        }
        
        # Создаем подпись
        signature_data = '|'.join([
            webhook_data['order_id'],
            webhook_data['payment_id'],
            webhook_data['status'],
            str(webhook_data['amount']),
            webhook_data['currency']
        ])
        signature = hmac.new(
            b'portmone_secret_key',
            signature_data.encode('utf-8'),
            hashlib.sha1
        ).hexdigest()
        
        response = self.client.post(
            reverse('portmone-webhook'),
            data=webhook_data,
            content_type='application/json',
            HTTP_SIGNATURE=signature
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Проверяем что платеж обновился
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'paid')


class WebhookSecurityTests(WebhookTestCase):
    """Тесты безопасности webhook'ов"""
    
    def test_webhook_without_signature(self):
        """Тест webhook'а без подписи"""
        webhook_data = {
            'order_id': str(self.order.id),
            'status': 'success'
        }
        
        response = self.client.post(
            reverse('stripe-webhook'),
            data=webhook_data,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_webhook_with_invalid_json(self):
        """Тест webhook'а с неверным JSON"""
        invalid_json = "{ invalid json }"
        
        response = self.client.post(
            reverse('stripe-webhook'),
            data=invalid_json,
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_webhook_replay_attack(self):
        """Тест защиты от replay атак"""
        # Создаем настройки
        payment_settings = PaymentSettings.objects.create(
            payment_system='stripe',
            is_active=True
        )
        payment_settings.webhook_secret = 'whsec_test_secret'
        payment_settings.save()
        
        webhook_data = {
            'id': 'evt_test_123',
            'type': 'payment_intent.succeeded',
            'data': {
                'object': {
                    'id': 'pi_test_123',
                    'status': 'succeeded'
                }
            }
        }
        
        payload = json.dumps(webhook_data).encode('utf-8')
        signature = f"t={int(1234567890)},v1={hmac.new(b'whsec_test_secret', payload, hashlib.sha256).hexdigest()}"
        
        # Первый запрос должен пройти
        response1 = self.client.post(
            reverse('stripe-webhook'),
            data=payload,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE=signature
        )
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Повторный запрос с тем же ID должен быть отклонен
        response2 = self.client.post(
            reverse('stripe-webhook'),
            data=payload,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE=signature
        )
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_webhook_unknown_event_type(self):
        """Тест webhook'а с неизвестным типом события"""
        webhook_data = {
            'id': 'evt_test_123',
            'type': 'unknown.event.type',
            'data': {
                'object': {
                    'id': 'pi_test_123'
                }
            }
        }
        
        response = self.client.post(
            reverse('stripe-webhook'),
            data=webhook_data,
            content_type='application/json'
        )
        
        # Должен вернуть 200 OK, но не обрабатывать событие
        self.assertEqual(response.status_code, status.HTTP_200_OK) 