from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import PaymentSettings, Payment, Order
import stripe
import requests
from .permissions import IsAdminOrUser


class CreatePaymentView(APIView):
    permission_classes = [IsAdminOrUser]
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id, user=request.user)

            # Проверка существующего платежа
            if Payment.objects.filter(order=order, status='paid').exists():
                return Response({'error': 'Заказ уже оплачен'}, status=status.HTTP_400_BAD_REQUEST)

            payment_settings = PaymentSettings.objects.filter(is_active=True).first()
            if not payment_settings:
                return Response({'error': 'Платежная система не настроена'}, status=status.HTTP_400_BAD_REQUEST)

            # Инициализация платежа в Stripe
            if payment_settings.payment_system == 'stripe':
                stripe.api_key = payment_settings.secret_key

                session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'rub',
                            'product_data': {
                                'name': f'Заказ #{order.id}',
                            },
                            'unit_amount': int(order.total_price * 100),
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url=request.build_absolute_uri(f'/orders/{order.id}/success/'),
                    cancel_url=request.build_absolute_uri(f'/orders/{order.id}/cancel/'),
                    metadata={'order_id': order.id}
                )

                # Сохранение платежа
                payment = Payment.objects.create(
                    order=order,
                    amount=order.total_price,
                    external_id=session.id,
                    raw_response=session
                )

                return Response({'payment_url': session.url}, status=status.HTTP_201_CREATED)

            # Сюда вставить другие платежки

        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
                payment.status = 'paid'
                payment.save()

                # можно обновить заказ, если нужно
                order = payment.order
                order.status = 'paid'  # если у тебя есть статус
                order.save()

            except Payment.DoesNotExist:
                return Response({'error': 'Платёж не найден'}, status=404)

        return Response({'status': 'success'}, status=200)