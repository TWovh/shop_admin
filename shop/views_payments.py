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

from .serializers import PaymentSettingsSerializer

logger = logging.getLogger(__name__)

class CreatePaymentView(APIView):
    permission_classes = [IsAdminOrUser]

    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            if order.status != 'pending':
                return Response({'error': 'Заказ не может быть оплачен'}, status=400)

            if Payment.objects.filter(order=order, status='paid').exists():
                return Response({'error': 'Уже оплачен'}, status=400)

            payment_settings = PaymentSettings.objects.filter(is_active=True).first()
            if not payment_settings:
                return Response({'error': 'Нет настроенной платежной системы'}, status=400)

            system = payment_settings.payment_system
            if system == 'stripe':
                return self.create_stripe(order, payment_settings)
            elif system == 'paypal':
                return self.create_paypal(order, payment_settings)
            elif system == 'fondy':
                return self.create_fondy(order, payment_settings)
            elif system == 'liqpay':
                return self.create_liqpay(order, payment_settings)

            return Response({'error': 'Неподдерживаемая система'}, status=400)

        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=404)

    def create_stripe(self, order, settings):
        import stripe
        stripe.api_key = settings.secret_key

        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'uah',
                    'product_data': {'name': f'Заказ #{order.id}'},
                    'unit_amount': int(order.total_price * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=f'{settings.SITE_URL}/orders/{order.id}/success/',
            cancel_url=f'{settings.SITE_URL}/orders/{order.id}/cancel/',
            metadata={'order_id': order.id}
        )

        Payment.objects.create(
            order=order,
            amount=order.total_price,
            external_id=session.id,
            payment_system='stripe',
            raw_response=session,
            status='pending'
        )

        return Response({'payment_url': session.url})

    def create_paypal(self, order, settings):
        return Response({'payment_url': f'https://www.sandbox.paypal.com/checkoutnow?token=FAKE-PAYPAL-TOKEN-{order.id}'})

    def create_fondy(self, order, settings):
        return Response({'payment_url': f'https://pay.fondy.eu/sandbox/pay/FONDY-MOCK-ID-{order.id}'})

    def create_liqpay(self, order, settings):
        return Response({'payment_url': f'https://www.liqpay.ua/sandbox/checkout?order_id={order.id}'})

#для админки
class PaymentMethodsView(APIView):
    def get(self, request):
        # Получаем все активные платёжные системы
        methods = PaymentSettings.objects.filter(is_active=True)
        data = []

        for method in methods:
            data.append({
                "id": method.id,
                "name": method.get_payment_system_display(),  # Получаем красивое имя
                "system": method.payment_system,  # Например: stripe, fondy и т.д.
                "sandbox": method.sandbox,  # true / false
            })

        return Response(data)

#для фронта
class PaymentOptionsAPIView(APIView):
    def get(self, request):
        active_systems = PaymentSettings.objects.filter(is_active=True)
        options = [
            {
                "system": s.payment_system,
                "name": s.get_payment_system_display()
            }
            for s in active_systems
        ]
        return Response(options)


class ActivePaymentSystemsView(APIView):
    def get(self, request):
        active_payments = PaymentSettings.objects.filter(is_active=True)
        serializer = PaymentSettingsSerializer(active_payments, many=True)
        return Response(serializer.data)

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