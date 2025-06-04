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


class PaymentWebhookView(APIView):
    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
        payment_settings = PaymentSettings.objects.filter(payment_system='stripe', is_active=True).first()

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, payment_settings.webhook_secret
            )

            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                payment = Payment.objects.get(external_id=session['id'])
                payment.status = 'paid'
                payment.raw_response = event
                payment.save()

                # Обновление статуса заказа
                order = payment.order
                order.status = 'processing'  # Меняем статус на "В обработке"
                order.save()

            return Response(status=status.HTTP_200_OK)

        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Payment.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)