from .models import NovaPoshtaSettings
import base64
import hashlib
import json
import requests
import stripe

def get_nova_poshta_api_key():
    settings = NovaPoshtaSettings.objects.order_by("-updated_at").first()
    if settings:
        return settings.api_key
    return None

def test_payment_connection(settings):
    try:
        system = settings.payment_system

        if system == 'stripe':
            stripe.api_key = settings.secret_key
            stripe.Balance.retrieve()
            return True, "Stripe успешно подключен"

        elif system == 'paypal':
            response = requests.post(
                'https://api.sandbox.paypal.com/v1/oauth2/token',
                auth=(settings.api_key, settings.secret_key),
                data={'grant_type': 'client_credentials'}
            )
            if response.status_code == 200:
                return True, "PayPal успешно подключен"
            else:
                raise Exception(response.text)

        elif system == 'portmone':
            headers = {'Content-Type': 'application/json'}
            data = {
                "payee_id": settings.api_key,
                "login": settings.api_key,
                "password": settings.secret_key,
            }
            response = requests.post(
                'https://api.portmone.com.ua/rest/merchant/login',
                json=data,
                headers=headers
            )
            if response.status_code == 200 and 'token' in response.text:
                return True, "Portmone успешно подключен"
            else:
                raise Exception(response.text)

        elif system == 'liqpay':
            public_key = settings.api_key
            private_key = settings.secret_key
            payload = {
                "public_key": public_key,
                "version": "3",
                "action": "status",
                "order_id": "test-order-id"
            }
            data_str = base64.b64encode(json.dumps(payload).encode()).decode()
            sign_str = private_key + data_str + private_key
            signature = base64.b64encode(hashlib.sha1(sign_str.encode()).digest()).decode()

            response = requests.post(
                'https://www.liqpay.ua/api/request',
                data={"data": data_str, "signature": signature}
            )
            if response.status_code == 200 and 'status' in response.json():
                return True, "LiqPay успешно подключен"
            else:
                raise Exception(response.text)

        elif system == 'fondy':
            merchant_id = settings.api_key
            secret_key = settings.secret_key
            request_data = {
                "request": {
                    "server_callback_url": "https://example.com",
                    "merchant_id": merchant_id,
                    "order_id": "test-fondy-order-id",
                    "amount": 100,
                    "currency": "UAH"
                }
            }
            data_str = json.dumps(request_data["request"], separators=(',', ':'))
            signature = hashlib.sha1((secret_key + data_str + secret_key).encode()).hexdigest()
            request_data["request"]["signature"] = signature

            response = requests.post(
                "https://api.fondy.eu/api/checkout/status",
                json=request_data
            )

            if response.status_code == 200 and response.json().get("response", {}).get("order_status"):
                return True, "Fondy успешно подключен"
            else:
                raise Exception(response.text)

        else:
            raise NotImplementedError(f"Проверка не реализована для {system}")

    except Exception as e:
        return False, str(e)