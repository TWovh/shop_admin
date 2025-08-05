import logging
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from .models import NovaPoshtaSettings
import base64
import hashlib
import json
import requests
import stripe

logger = logging.getLogger(__name__)

def get_nova_poshta_api_key():
    settings = NovaPoshtaSettings.objects.order_by("-updated_at").first()
    if settings:
        return settings.api_key
    return None

def send_payment_confirmation_email(order, payment):
    try:
        subject = f"Оплата заказа #{order.id} подтверждена"
        to_email = order.email
        from_email = settings.DEFAULT_FROM_EMAIL

        context = {
            "order": order,
            "user": order.user,
            "items": order.order_items.all(),
            "payment": payment,
        }

        html = render_to_string("email/payment_success.html", context)
        msg = EmailMultiAlternatives(subject, "", from_email, [to_email])
        msg.attach_alternative(html, "text/html")
        msg.send()
        
        logger.info(f"Payment confirmation email sent to {to_email} for order {order.id}")
        
    except Exception as e:
        logger.error(f"Failed to send payment confirmation email for order {order.id}: {e}")

def test_payment_connection(settings):
    """Тестирует подключение к платежной системе"""
    try:
        system = settings.payment_system
        logger.info(f"Testing connection to {system} payment system")

        if system == 'stripe':
            return _test_stripe_connection(settings)
        elif system == 'paypal':
            return _test_paypal_connection(settings)
        elif system == 'portmone':
            return _test_portmone_connection(settings)
        elif system == 'liqpay':
            return _test_liqpay_connection(settings)
        elif system == 'fondy':
            return _test_fondy_connection(settings)
        else:
            error_msg = f"Проверка не реализована для {system}"
            logger.error(error_msg)
            return False, error_msg

    except Exception as e:
        logger.error(f"Error testing {settings.payment_system} connection: {e}", exc_info=True)
        return False, str(e)

def _test_stripe_connection(settings):
    """Тестирует подключение к Stripe"""
    try:
        stripe.api_key = settings.secret_key
        balance = stripe.Balance.retrieve()
        logger.info("Stripe connection test successful")
        return True, "Stripe успешно подключен"
    except stripe.error.AuthenticationError:
        error_msg = "Неверный API ключ Stripe"
        logger.error(error_msg)
        return False, error_msg
    except stripe.error.APIConnectionError:
        error_msg = "Ошибка подключения к Stripe API"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Ошибка подключения к Stripe: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def _test_paypal_connection(settings):
    """Тестирует подключение к PayPal"""
    try:
        base_url = "https://api.sandbox.paypal.com" if settings.is_sandbox else "https://api-m.paypal.com"
        response = requests.post(
            f'{base_url}/v1/oauth2/token',
            auth=(settings.api_key, settings.secret_key),
            data={'grant_type': 'client_credentials'},
            timeout=10
        )
        
        if response.status_code == 200:
            logger.info("PayPal connection test successful")
            return True, "PayPal успешно подключен"
        else:
            error_msg = f"PayPal API вернул статус {response.status_code}: {response.text}"
            logger.error(error_msg)
            return False, error_msg
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка подключения к PayPal API: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Ошибка подключения к PayPal: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def _test_portmone_connection(settings):
    """Тестирует подключение к Portmone"""
    try:
        headers = {'Content-Type': 'application/json'}
        data = {
            "payee_id": settings.api_key,
            "login": settings.api_key,
            "password": settings.secret_key,
        }
        
        response = requests.post(
            'https://api.portmone.com.ua/rest/merchant/login',
            json=data,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200 and 'token' in response.text:
            logger.info("Portmone connection test successful")
            return True, "Portmone успешно подключен"
        else:
            error_msg = f"Portmone API вернул статус {response.status_code}: {response.text}"
            logger.error(error_msg)
            return False, error_msg
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка подключения к Portmone API: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Ошибка подключения к Portmone: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def _test_liqpay_connection(settings):
    """Тестирует подключение к LiqPay"""
    try:
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
            data={"data": data_str, "signature": signature},
            timeout=10
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if 'status' in response_data:
                logger.info("LiqPay connection test successful")
                return True, "LiqPay успешно подключен"
            else:
                error_msg = f"LiqPay API вернул неожиданный ответ: {response_data}"
                logger.error(error_msg)
                return False, error_msg
        else:
            error_msg = f"LiqPay API вернул статус {response.status_code}: {response.text}"
            logger.error(error_msg)
            return False, error_msg
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка подключения к LiqPay API: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Ошибка подключения к LiqPay: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def _test_fondy_connection(settings):
    """Тестирует подключение к Fondy"""
    try:
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
            json=request_data,
            timeout=10
        )

        if response.status_code == 200:
            response_data = response.json()
            if response_data.get("response", {}).get("order_status"):
                logger.info("Fondy connection test successful")
                return True, "Fondy успешно подключен"
            else:
                error_msg = f"Fondy API вернул неожиданный ответ: {response_data}"
                logger.error(error_msg)
                return False, error_msg
        else:
            error_msg = f"Fondy API вернул статус {response.status_code}: {response.text}"
            logger.error(error_msg)
            return False, error_msg
            
    except requests.exceptions.RequestException as e:
        error_msg = f"Ошибка подключения к Fondy API: {str(e)}"
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Ошибка подключения к Fondy: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


