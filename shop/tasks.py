"""
Асинхронные задачи для приложения shop
"""
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from .models import Order, Payment, NovaPoshtaSettings
from .constants import PAYMENT_STATUS_PAID, ORDER_STATUS_COMPLETED
from django.db import models

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_payment_success_email_task(self, order_id):
    """
    Отправка email о успешной оплате заказа
    """
    try:
        order = Order.objects.get(id=order_id)
        
        context = {
            'order': order,
            'order_items': order.order_items.all(),
            'payment': order.payments.filter(status=PAYMENT_STATUS_PAID).first()
        }
        
        html_message = render_to_string('email/payment_success.html', context)
        text_message = render_to_string('email/payment_success.txt', context)
        
        send_mail(
            subject=f'Оплата заказа #{order.id} подтверждена',
            message=text_message,
            from_email='noreply@yourshop.com',
            recipient_list=[order.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Payment success email sent for order {order_id}")
        return True
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for email sending")
        return False
    except Exception as e:
        logger.error(f"Failed to send payment email for order {order_id}: {str(e)}")
        # Повторяем задачу при ошибке
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def create_nova_poshta_ttn_task(self, order_id):
    """
    Создание TTN в Nova Poshta
    """
    try:
        order = Order.objects.get(id=order_id)
        
        if order.delivery_method != 'nova_poshta':
            logger.info(f"Order {order_id} is not Nova Poshta delivery")
            return False
            
        # Получаем настройки Nova Poshta
        nova_settings = NovaPoshtaSettings.objects.filter(is_active=True).first()
        if not nova_settings:
            logger.error("No active Nova Poshta settings found")
            return False
            
        # Используем существующую функцию create_ttn из views.py
        from .views import create_ttn
        
        result = create_ttn(order, settings=nova_settings)
        
        if result.get('success'):
            logger.info(f"TTN created for order {order_id}: {result.get('ttn')}")
            return True
        else:
            logger.error(f"Failed to create TTN for order {order_id}: {result.get('message')}")
            raise self.retry(exc=Exception(result.get('message')))
            
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for TTN creation")
        return False
    except Exception as e:
        logger.error(f"Error creating TTN for order {order_id}: {str(e)}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def process_webhook_task(self, webhook_data, payment_system):
    """
    Обработка webhook в фоновом режиме
    """
    try:
        logger.info(f"Processing {payment_system} webhook: {webhook_data}")
        
        # обработка webhook добавить
        
        logger.info(f"Webhook {payment_system} processed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        raise self.retry(exc=e)


@shared_task
def cleanup_old_payments_task():
    """
    Очистка старых неоплаченных платежей (старше 7 дней)
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        old_payments = Payment.objects.filter(
            status='pending',
            created_at__lt=cutoff_date
        )
        
        count = old_payments.count()
        old_payments.delete()
        
        logger.info(f"Cleaned up {count} old pending payments")
        return count
        
    except Exception as e:
        logger.error(f"Error cleaning up old payments: {str(e)}")
        return 0


@shared_task
def cleanup_old_orders_task():
    """
    Очистка старых отмененных заказов (старше 30 дней)
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        old_orders = Order.objects.filter(
            status='cancelled',
            created_at__lt=cutoff_date
        )
        
        count = old_orders.count()
        old_orders.delete()
        
        logger.info(f"Cleaned up {count} old cancelled orders")
        return count
        
    except Exception as e:
        logger.error(f"Error cleaning up old orders: {str(e)}")
        return 0


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_status_update_email_task(self, order_id, old_status, new_status):
    """
    Отправка email об изменении статуса заказа
    """
    try:
        order = Order.objects.get(id=order_id)
        
        context = {
            'order': order,
            'old_status': old_status,
            'new_status': new_status,
            'order_items': order.order_items.all()
        }
        
        html_message = render_to_string('email/order_status_update.html', context)
        text_message = render_to_string('email/order_status_update.txt', context)
        
        send_mail(
            subject=f'Статус заказа #{order.id} изменен',
            message=text_message,
            from_email='noreply@yourshop.com',
            recipient_list=[order.email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Order status update email sent for order {order_id}")
        return True
        
    except Order.DoesNotExist:
        logger.error(f"Order {order_id} not found for status update email")
        return False
    except Exception as e:
        logger.error(f"Failed to send status update email for order {order_id}: {str(e)}")
        raise self.retry(exc=e)


