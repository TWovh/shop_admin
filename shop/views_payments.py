import base64
import hashlib
import json

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.generics import RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from .clients import StripeClient, PayPalClient, FondyClient, LiqPayClient, PortmoneClient
from .models import PaymentSettings, Payment, Order
import stripe
from .permissions import IsAdminOrUser
from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging
from .serializers import PaymentSettingsSerializer, PaymentMethodSerializer, PaymentDetailSerializer

logger = logging.getLogger(__name__)

class CreatePaymentView(APIView):
    permission_classes = [IsAdminOrUser]

    def post(self, request, order_id):
        payment_system = request.data.get('payment_system')

        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=404)

        if order.status != 'pending':
            return Response({'error': 'Заказ не может быть оплачен'}, status=400)

        if Payment.objects.filter(order=order, status='paid').exists():
            return Response({'error': 'Заказ уже оплачен'}, status=400)

        if not payment_system:
            return Response({'error': 'Не указана платежная система'}, status=400)

        try:
            payment_settings = PaymentSettings.objects.get(payment_system=payment_system, is_active=True)
        except PaymentSettings.DoesNotExist:
            return Response({'error': 'Платежная система неактивна или не настроена'}, status=400)

        raw = None
        system = payment_system
        if system == 'stripe':
            client = StripeClient(payment_settings)
            ext_id, url = client.create_checkout(order)
        elif system == 'paypal':
            client = PayPalClient(payment_settings)
            ext_id, url, raw = client.create_order(order)
        elif system == 'fondy':
            client = FondyClient(payment_settings)
            ext_id, url, raw = client.create_payment(order)
        elif system == 'liqpay':
            client = LiqPayClient(payment_settings)
            data_b64, sign = client.create_form(order)
            # сохраним raw = {data, sign}
            raw = {'data': data_b64, 'signature': sign}
            # вернём оба параметра фронту
            ext_id = order.id
            url = client.API_URL
        elif system == 'portmone':
            client = PortmoneClient(payment_settings)
            ext_id, url, raw = client.create_payment(order)
        else:
            return Response({'error': 'Unsupported'}, status=400)

        payment = Payment.objects.create(
            order=order,
            user=self.request.user,
            amount=order.total_price,
            payment_system=system,
            external_id=ext_id,
            raw_response=raw or {},
            status='pending'
        )

        if system == 'liqpay':
            return Response({
                'checkout_url': url,
                'data': raw['data'],
                'signature': raw['signature']
            })

        return Response({'payment_url': url})





class PaymentDetailView(RetrieveAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentDetailSerializer
    permission_classes = [IsAdminOrUser]

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

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

class ActivePaymentMethodsAPIView(APIView):
    def get(self, request):
        active_settings = PaymentSettings.objects.filter(is_active=True)
        serializer = PaymentMethodSerializer(active_settings, many=True)
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


@method_decorator(csrf_exempt, name='dispatch')
class FondyWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data.get('response') or request.data
        order_id = data.get('order_id')
        payment_id = data.get('payment_id')
        status = data.get('order_status')

        if status != 'approved':
            return Response({'status': 'ignored'}, status=200)

        try:
            payment = Payment.objects.get(order__id=order_id, external_id=payment_id)
            payment.status = 'paid'
            payment.save()

            order = payment.order
            order.status = 'paid'
            order.save()

            # по желанию
            # self.send_payment_success_email(payment)

            return Response({'status': 'success'})
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
class PayPalWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        event = request.data
        resource = event.get('resource', {})
        event_type = event.get('event_type')

        if event_type == 'CHECKOUT.ORDER.APPROVED':
            external_id = resource.get('id')
            try:
                payment = Payment.objects.get(external_id=external_id)
                payment.status = 'paid'
                payment.save()

                order = payment.order
                order.status = 'paid'
                order.save()

                return Response({'status': 'success'})
            except Payment.DoesNotExist:
                return Response({'error': 'Payment not found'}, status=404)
        return Response({'status': 'ignored'})



@method_decorator(csrf_exempt, name='dispatch')
class LiqPayWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        data_b64 = request.data.get('data')
        signature = request.data.get('signature')

        if not data_b64 or not signature:
            return Response({'error': 'Invalid payload'}, status=400)

        private_key = settings.LIQPAY_PRIVATE_KEY
        expected_signature = base64.b64encode(
            hashlib.sha1((private_key + data_b64 + private_key).encode()).digest()
        ).decode()

        if signature != expected_signature:
            return Response({'error': 'Invalid signature'}, status=400)

        data_json = base64.b64decode(data_b64).decode('utf-8')
        data = json.loads(data_json)

        if data.get('status') != 'success':
            return Response({'status': 'ignored'}, status=200)

        order_id = data.get('order_id')

        try:
            payment = Payment.objects.get(order__id=order_id)
            payment.status = 'paid'
            payment.save()

            order = payment.order
            order.status = 'paid'
            order.save()

            return Response({'status': 'success'})
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=404)


@method_decorator(csrf_exempt, name='dispatch')
class PortmoneWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        data = request.data
        order_id = data.get('order_id')
        status = data.get('status')
        payment_id = data.get('payment_id')

        if status != 'PAYED':
            return Response({'status': 'ignored'})

        try:
            payment = Payment.objects.get(order__id=order_id, external_id=payment_id)
            payment.status = 'paid'
            payment.save()

            order = payment.order
            order.status = 'paid'
            order.save()

            return Response({'status': 'success'})
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=404)