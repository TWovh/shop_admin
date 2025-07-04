from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import PaymentSettings, Payment, Order
import stripe
from .permissions import IsAdminOrUser
from django.core.mail import send_mail
from django.template.loader import render_to_string
from decimal import Decimal
import logging


logger = logging.getLogger(__name__)

class CreatePaymentView(APIView):
    permission_classes = [IsAdminOrUser]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)

            if order.status != 'pending':
                return Response({'error': 'Заказ не может быть оплачен'}, status=status.HTTP_400_BAD_REQUEST)

            if Payment.objects.filter(order=order, status='paid').exists():
                return Response({'error': 'Заказ уже оплачен'}, status=status.HTTP_400_BAD_REQUEST)

            payment_settings = PaymentSettings.objects.filter(is_active=True).first()
            if not payment_settings:
                return Response({'error': 'Платежная система не настроена'}, status=status.HTTP_400_BAD_REQUEST)

            if payment_settings.payment_system == 'stripe':
                return self.create_stripe_payment(order, payment_settings)

            return Response({'error': 'Неизвестная платёжная система'}, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception("Ошибка при создании платежа")
            return Response({'error': 'Внутренняя ошибка сервера'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create_stripe_payment(self, order, payment_settings):
        stripe.api_key = payment_settings.secret_key  # используем зашифрованный ключ из модели

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'uah',
                    'product_data': {
                        'name': f'Заказ #{order.id}',
                    },
                    'unit_amount': int(Decimal(order.total_price) * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{settings.SITE_URL}/orders/{order.id}/success/',
            cancel_url=f'{settings.SITE_URL}/orders/{order.id}/cancel/',
            metadata={'order_id': order.id}
        )

        payment = Payment.objects.create(
            order=order,
            amount=order.total_price,
            external_id=session.id,
            payment_system='stripe',
            raw_response=session,
            status='pending'
        )

        return Response({'payment_url': session.url}, status=status.HTTP_201_CREATED)

@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET  #

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError as e:
            return Response({'error': 'Invalid payload'}, status=400)
        except stripe.error.SignatureVerificationError as e:
            return Response({'error': 'Invalid signature'}, status=400)

        # Обработка успешной оплаты
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            order_id = session['metadata'].get('order_id')
            session_id = session['id']

            try:
                payment = Payment.objects.get(external_id=session_id)
                if str(payment.order.id) != str(order_id):
                    return Response({'error': 'Несоответствие order_id'}, status=400)

                payment.status = 'paid'
                payment.save()
                try:
                    self.send_payment_success_email(payment)
                except Exception as e:
                    # логируй ошибку или отправь в sentry
                    pass

                # можно обновить заказ, если нужно
                order = payment.order
                order.status = 'paid'  # если у тебя есть статус
                order.save()


            except Payment.DoesNotExist:
                return Response({'error': 'Платёж не найден'}, status=404)


        return Response({'status': 'success'}, status=200)

    def send_payment_success_email(self, payment):
        subject = f"Заказ #{payment.order.id} успешно оплачен"

        # Инвойс
        context = {
            'order': payment.order,
            'payment': payment,
            'site_url': settings.SITE_URL
        }

        # HTML версия письма
        html_message = render_to_string('email/payment_success.html', context)

        # Текстовая версия письма
        plain_message = render_to_string('email/payment_success.txt', context)

        # Отправка покупателю
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [payment.order.email],
            html_message=html_message
        )

        # Отправка администратору
        admin_subject = f"Новый оплаченный заказ #{payment.order.id}"
        send_mail(
            admin_subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            html_message=html_message
        )