import base64
import hashlib
import hmac
import json
import requests
from decimal import Decimal

from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings

class StripeClient:
    def __init__(self, config):
        import stripe
        stripe.api_key = config.secret_key
        self.stripe = stripe

    def create_checkout(self, order):
        session = self.stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'uah',
                    'product_data': {'name': f'Заказ #{order.id}'},
                    'unit_amount': int(Decimal(order.total_price) * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f"{settings.FRONTEND_URL}/order-success/{order.id}",
            cancel_url=f"{settings.FRONTEND_URL}/order-cancel/{order.id}",
            metadata={'order_id': order.id}
        )
        return session.id, session.url

class PayPalClient:
    BASE = "https://api-m.sandbox.paypal.com"  # для песочницы
    def __init__(self, config):
        self.client_id = config.api_key
        self.client_secret = config.secret_key

    def get_token(self):
        r = requests.post(
            f"{self.BASE}/v1/oauth2/token",
            auth=(self.client_id, self.client_secret),
            data={'grant_type': 'client_credentials'}
        )
        r.raise_for_status()
        return r.json()['access_token']

    def create_order(self, order):
        token = self.get_token()
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": str(order.id),
                "amount": {
                    "currency_code": "UAH",
                    "value": str(order.total_price)
                }
            }],
            "application_context": {
                "return_url": f"{settings.SITE_URL}{reverse('order-success', args=[order.id])}",
                "cancel_url": f"{settings.SITE_URL}{reverse('order-cancel', args=[order.id])}"
            }
        }
        r = requests.post(f"{self.BASE}/v2/checkout/orders", headers=headers, json=data)
        r.raise_for_status()
        js = r.json()
        # external_id = js['id'], ссылка из links
        external_id = js['id']
        approve = next(link['href'] for link in js['links'] if link['rel']=='approve')
        return external_id, approve, js

class FondyClient:
    BASE = "https://api.fondy.eu/api/"
    def __init__(self, config):
        self.merchant_id = config.api_key
        self.secret = config.secret_key

    def create_payment(self, order):
        data = {
            "order_id": str(order.id),
            "merchant_id": self.merchant_id,
            "currency": "UAH",
            "amount": int(Decimal(order.total_price) * 100),
            "order_desc": f"Заказ #{order.id}",
            "response_url": f"{settings.SITE_URL}{reverse('order-success', args=[order.id])}",
            "server_callback_url": f"{settings.SITE_URL}{reverse('fondy-webhook')}"
        }
        # Signature: SHA1 of sorted values + secret
        signature = self._make_signature(data)
        data['signature'] = signature
        r = requests.post(f"{self.BASE}checkout", json=data)
        r.raise_for_status()
        js = r.json()['response']
        return js['payment_id'], js['checkout_url'], js

    def _make_signature(self, data):
        # пример: сортировка ключей и формирование строки
        params = [str(data[k]) for k in sorted(data) if k!='signature']
        sign_string = '|'.join(params) + f"|{self.secret}"
        return hashlib.sha1(sign_string.encode('utf-8')).hexdigest()

class LiqPayClient:
    API_URL = "https://www.liqpay.ua/api/3/checkout"

    def __init__(self, config):
        self.public_key = config.api_key
        self.private_key = config.secret_key
        self.is_sandbox = config.is_sandbox

    def create_form(self, order):
        data = {
            "public_key": self.public_key,
            "version": "3",
            "action": "pay",
            "amount": str(order.total_price),
            "currency": "UAH",
            "description": f"Оплата заказа #{order.id}",
            "order_id": f"{order.id}",
            "language": "uk",
            "server_url": f"{settings.BACKEND_URL}/api/liqpay/",
            "result_url": f"{settings.FRONTEND_URL}/order-success/{order.id}",
        }

        if self.is_sandbox:
            data["sandbox"] = 1

        data_json = json.dumps(data)
        data_b64 = base64.b64encode(data_json.encode()).decode()
        sign_str = self.private_key + data_b64 + self.private_key
        signature = base64.b64encode(hashlib.sha1(sign_str.encode()).digest()).decode()
        return data_b64, signature

class PortmoneClient:
    BASE = "https://www.portmone.com.ua/gateway/"

    def __init__(self, config):
        self.merchant_id = config.api_key
        self.secret = config.secret_key
        self.sandbox = config.sandbox

    def create_payment(self, order):
        payload = {
            "payee_id": self.merchant_id,
            "shop_order_number": str(order.id),
            "bill_amount": str(order.total_price),
            "description": f"Оплата заказа №{order.id}",
            "success_url": f"{settings.SITE_URL}{reverse('order-success', args=[order.id])}",
            "failure_url": f"{settings.SITE_URL}{reverse('order-failed', args=[order.id])}",
            "callback_url": f"{settings.SITE_URL}{reverse('portmone-webhook')}",
            "lang": "UA",
        }

        form_html = render_to_string("payments/portmone_form.html", {
            "action_url": self.BASE,
            "payload": payload,
        })

        return {
            "payment_id": order.id,
            "payment_html": form_html,
            "payload": payload
        }

    def _make_signature(self, payload):
        params = [str(payload[k]) for k in sorted(payload) if k!='signature']
        s = "|".join(params) + f"|{self.secret}"
        return hashlib.sha1(s.encode()).hexdigest()