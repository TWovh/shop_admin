import base64
import hashlib
import json
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView
from rest_framework.response import Response
from .clients import StripeClient, PayPalClient, FondyClient, LiqPayClient, PortmoneClient
from .models import PaymentSettings, Payment, Order
from .permissions import IsAdminOrUser
import logging
from .serializers import PaymentSettingsSerializer, PaymentMethodSerializer, PaymentDetailSerializer
from .utils import send_payment_confirmation_email

logger = logging.getLogger(__name__)

class CreatePaymentView(APIView):
    permission_classes = [IsAdminOrUser]

    def post(self, request, order_id):
        try:
            logger.info(f"CreatePaymentView: User {request.user.email}, role {getattr(request.user, 'role', None)}")
            
            payment_system = request.data.get('payment_system')
            if not payment_system:
                logger.error("CreatePaymentView: No payment system specified")
                return Response({'error': 'Не указана платежная система'}, status=400)

            # Получаем заказ
            try:
                order = Order.objects.get(id=order_id, user=request.user)
                logger.info(f"CreatePaymentView: Found order {order_id} for user {request.user.email}")
            except Order.DoesNotExist:
                logger.error(f"CreatePaymentView: Order {order_id} not found for user {request.user.email}")
                return Response({'error': 'Заказ не найден'}, status=404)

            # Проверяем права доступа
            if order.user != request.user:
                logger.error(f"CreatePaymentView: User {request.user.email} trying to access order {order_id} of user {order.user.email}")
                return Response({'error': 'Нет доступа к заказу'}, status=403)

            # Проверяем статус заказа
            if order.status != 'pending':
                logger.warning(f"CreatePaymentView: Order {order_id} has status {order.status}, cannot be paid")
                return Response({'error': 'Заказ не может быть оплачен'}, status=400)

            # Проверяем, не оплачен ли уже заказ
            if Payment.objects.filter(order=order, status='paid').exists():
                logger.warning(f"CreatePaymentView: Order {order_id} already has paid payment")
                return Response({'error': 'Заказ уже оплачен'}, status=400)

            # Получаем настройки платежной системы
            try:
                payment_settings = PaymentSettings.objects.get(
                    payment_system=payment_system, 
                    is_active=True
                )
                logger.info(f"CreatePaymentView: Found active {payment_system} settings")
            except PaymentSettings.DoesNotExist:
                logger.error(f"CreatePaymentView: No active {payment_system} settings found")
                return Response({'error': 'Платежная система неактивна или не настроена'}, status=400)

            # Создаем платеж в зависимости от системы
            if payment_system == 'stripe':
                return self._create_stripe_payment(order, payment_settings)
            elif payment_system == 'paypal':
                return self._create_paypal_payment(order, payment_settings)
            elif payment_system == 'fondy':
                return self._create_fondy_payment(order, payment_settings)
            elif payment_system == 'liqpay':
                return self._create_liqpay_payment(order, payment_settings)
            elif payment_system == 'portmone':
                return self._create_portmone_payment(order, payment_settings)
            else:
                logger.error(f"CreatePaymentView: Unsupported payment system {payment_system}")
                return Response({'error': 'Неподдерживаемая платежная система'}, status=400)

        except Exception as e:
            logger.error(f"CreatePaymentView error: {str(e)}", exc_info=True)
            return Response({'error': 'Внутренняя ошибка сервера'}, status=500)

    def _create_stripe_payment(self, order, payment_settings):
        """Создание платежа через Stripe"""
        try:
            client = StripeClient(payment_settings)
            session_id, url = client.create_checkout(order)

            Payment.objects.create(
                order=order,
                user=self.request.user,
                amount=order.total_price,
                payment_system='stripe',
                external_id=session_id,
                raw_response={},
                status='pending'
            )

            logger.info(f"Created Stripe payment for order {order.id}, session_id: {session_id}")
            return Response({'session_id': session_id, 'payment_url': url})

        except Exception as e:
            logger.error(f"Stripe payment creation error: {str(e)}", exc_info=True)
            return Response({'error': f'Ошибка создания платежа Stripe: {str(e)}'}, status=500)

    def _create_paypal_payment(self, order, payment_settings):
        """Создание платежа через PayPal"""
        try:
            client = PayPalClient(payment_settings)
            ext_id, url, raw = client.create_order(order)
            
            Payment.objects.create(
                order=order,
                user=self.request.user,
                amount=order.total_price,
                payment_system='paypal',
                external_id=ext_id,
                raw_response=raw,
                status='pending'
            )

            logger.info(f"Created PayPal payment for order {order.id}, external_id: {ext_id}")
            return Response({'payment_url': url})

        except Exception as e:
            logger.error(f"PayPal payment creation error: {str(e)}", exc_info=True)
            return Response({'error': f'Ошибка создания платежа PayPal: {str(e)}'}, status=500)

    def _create_fondy_payment(self, order, payment_settings):
        """Создание платежа через Fondy"""
        try:
            client = FondyClient(payment_settings)
            ext_id, url, raw = client.create_payment(order)
            
            Payment.objects.create(
                order=order,
                user=self.request.user,
                amount=order.total_price,
                payment_system='fondy',
                external_id=ext_id,
                raw_response=raw,
                status='pending'
            )

            logger.info(f"Created Fondy payment for order {order.id}, external_id: {ext_id}")
            return Response({'payment_url': url})

        except Exception as e:
            logger.error(f"Fondy payment creation error: {str(e)}", exc_info=True)
            return Response({'error': f'Ошибка создания платежа Fondy: {str(e)}'}, status=500)

    def _create_liqpay_payment(self, order, payment_settings):
        """Создание платежа через LiqPay"""
        try:
            client = LiqPayClient(payment_settings)
            data_b64, sign = client.create_form(order)
            raw = {'data': data_b64, 'signature': sign}
            ext_id = order.id
            url = client.API_URL
            
            Payment.objects.create(
                order=order,
                user=self.request.user,
                amount=order.total_price,
                payment_system='liqpay',
                external_id=ext_id,
                raw_response=raw,
                status='pending'
            )

            logger.info(f"Created LiqPay payment for order {order.id}")
            return Response({'payment_url': url, 'form_data': raw})

        except Exception as e:
            logger.error(f"LiqPay payment creation error: {str(e)}", exc_info=True)
            return Response({'error': f'Ошибка создания платежа LiqPay: {str(e)}'}, status=500)

    def _create_portmone_payment(self, order, payment_settings):
        """Создание платежа через Portmone"""
        try:
            client = PortmoneClient(payment_settings)
            ext_id, url, raw = client.create_payment(order)
            
            Payment.objects.create(
                order=order,
                user=self.request.user,
                amount=order.total_price,
                payment_system='portmone',
                external_id=ext_id,
                raw_response=raw,
                status='pending'
            )

            logger.info(f"Created Portmone payment for order {order.id}, external_id: {ext_id}")
            return Response({'payment_url': url})

        except Exception as e:
            logger.error(f"Portmone payment creation error: {str(e)}", exc_info=True)
            return Response({'error': f'Ошибка создания платежа Portmone: {str(e)}'}, status=500)



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
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active = PaymentSettings.objects.filter(is_active=True)
        serializer = PaymentSettingsSerializer(active, many=True)
        return Response(serializer.data)


class ActivePaymentMethodsAPIView(APIView):
    def get(self, request):
        active_settings = PaymentSettings.objects.filter(is_active=True)
        serializer = PaymentMethodSerializer(active_settings, many=True)
        return Response(serializer.data)



def _handle_successful_payment(system, order_id, external_id, raw_data):
    from decimal import Decimal
    from django.db import transaction
    from .models import Order, Payment

    try:
        logger.info(f"Processing successful payment: system={system}, order_id={order_id}, external_id={external_id}")
        
        # Получаем заказ
        try:
            order = Order.objects.get(id=order_id)
            logger.info(f"Found order {order_id} with status {order.status}, payment_status {order.payment_status}")
        except Order.DoesNotExist:
            logger.error(f"Order {order_id} not found for payment {system}")
            return False

        # Проверяем, не был ли заказ уже оплачен
        existing_payment = Payment.objects.filter(
            order=order, 
            status='paid'
        ).first()
        
        if existing_payment:
            logger.warning(f"Order {order_id} already has paid payment: {existing_payment.id}")
            return True

        # КРИТИЧНО: Используем транзакцию для атомарности
        try:
            with transaction.atomic():
                logger.info(f"Starting transaction for payment processing: order_id={order_id}")
                
                # Блокируем заказ для обновления (защита от race conditions)
                order = Order.objects.select_for_update().get(id=order_id)
                logger.info(f"Locked order {order_id} for update")
                
                # Обновим/создадим Payment
                payment, created = Payment.objects.get_or_create(
                    order=order,
                    payment_system=system,
                    defaults={
                        'user': order.user,
                        'amount': order.total_price or Decimal('0.00'),
                        'external_id': external_id,
                        'raw_response': raw_data,
                        'status': 'paid',
                    }
                )
                
                if not created:
                    payment.status = 'paid'
                    payment.external_id = external_id
                    payment.raw_response = raw_data
                    payment.save()
                    logger.info(f"Updated existing payment {payment.id} for order {order_id}")
                else:
                    logger.info(f"Created new payment {payment.id} for order {order_id}")

                # Обновим статусы заказа
                if order.payment_status != 'paid':
                    old_payment_status = order.payment_status
                    old_status = order.status
                    
                    order.payment_status = 'paid'
                    if order.status == 'pending':
                        order.status = 'processing'
                    
                    order.save()
                    logger.info(f"Updated order {order_id}: payment_status {old_payment_status}->{order.payment_status}, status {old_status}->{order.status}")
                else:
                    logger.info(f"Order {order_id} payment_status already 'paid', no update needed")
                
                logger.info(f"Transaction completed successfully for order {order_id}")
                
        except transaction.TransactionManagementError as e:
            logger.error(f"Transaction error for order {order_id}: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error during transaction for order {order_id}: {e}", exc_info=True)
            # Транзакция автоматически откатится
            return False
            
        # Только ПОСЛЕ успешного завершения транзакции запускаем Celery задачи
        
        try:
            from .tasks import send_payment_success_email_task, create_nova_poshta_ttn_task
            
            # Отправляем email асинхронно
            email_task = send_payment_success_email_task.delay(order.id)
            logger.info(f"Payment success email task scheduled for order {order_id}, task_id: {email_task.id}")
            
            # Создаем TTN асинхронно (если это Nova Poshta)
            if order.delivery_method == 'nova_poshta':
                ttn_task = create_nova_poshta_ttn_task.delay(order.id)
                logger.info(f"Nova Poshta TTN task scheduled for order {order_id}, task_id: {ttn_task.id}")
            else:
                logger.info(f"Order {order_id} not using Nova Poshta, skipping TTN creation")
                
        except Exception as e:
            logger.error(f"Failed to schedule background tasks for order {order_id}: {e}", exc_info=True)
            # Фоновые задачи не критичны, основная транзакция уже завершена успешно
            # Продолжаем выполнение

        logger.info(f"Successfully processed payment {system} for order {order_id}")
        return True

    except Exception as e:
        logger.error(f"Error processing successful payment {system} for order {order_id}: {e}", exc_info=True)
        return False


@csrf_exempt
def stripe_webhook(request):
    import stripe
    
    try:
        # Получаем настройки Stripe
        payment_settings = PaymentSettings.objects.filter(
            payment_system='stripe', 
            is_active=True
        ).first()
        
        if not payment_settings:
            logger.error("Stripe webhook: No active Stripe settings found")
            return JsonResponse({'error': 'No active Stripe settings'}, status=400)

        webhook_secret = payment_settings.webhook_secret
        if not webhook_secret:
            logger.error("Stripe webhook: No webhook secret configured")
            return JsonResponse({'error': 'No webhook secret configured'}, status=400)
            
        stripe.api_key = payment_settings.secret_key

        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        if not sig_header:
            logger.error("Stripe webhook: Missing signature header")
            return JsonResponse({'error': 'Missing signature header'}, status=400)

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except ValueError as e:
            logger.error(f"Stripe webhook: Invalid payload: {e}")
            return JsonResponse({'error': 'Invalid payload'}, status=400)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Stripe webhook: Invalid signature: {e}")
            return JsonResponse({'error': 'Invalid signature'}, status=400)
        except Exception as e:
            logger.error(f"Stripe webhook: Error constructing event: {e}")
            return JsonResponse({'error': str(e)}, status=400)

        logger.info(f"Stripe webhook received: {event['type']}")

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            metadata = session.get('metadata', {})
            
            logger.info(f"Stripe session metadata: {metadata}")

            order_id = metadata.get('order_id')
            if not order_id:
                logger.error("Stripe webhook: No order_id in metadata")
                return JsonResponse({'error': 'Missing order_id'}, status=400)

            try:
                order = Order.objects.get(id=order_id)
                logger.info(f"Found order {order_id} for Stripe payment")
            except Order.DoesNotExist:
                logger.error(f"Stripe webhook: Order {order_id} not found")
                return JsonResponse({'error': 'Order not found'}, status=404)

            success = _handle_successful_payment('stripe', order_id, session['id'], session)
            if success:
                logger.info(f"Successfully processed Stripe payment for order {order_id}")
            else:
                logger.error(f"Failed to process Stripe payment for order {order_id}")
                return JsonResponse({'error': 'Payment processing failed'}, status=500)

        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Stripe webhook error: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Internal server error'}, status=500)

class StripePublicKeyView(APIView):
    permission_classes = [AllowAny]
    renderer_classes = [JSONRenderer]

    def get(self, request):
        payment_settings = PaymentSettings.objects.filter(payment_system='stripe', is_active=True).first()
        if not payment_settings:
            return Response({"publicKey": None}, status=404)

        return Response({
            "publicKey": payment_settings.api_key
        })


class PayPalWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            # Получаем настройки PayPal
            payment_settings = PaymentSettings.objects.filter(
                payment_system='paypal', 
                is_active=True
            ).first()
            
            if not payment_settings:
                logger.error("PayPal webhook: No active PayPal settings found")
                return JsonResponse({'error': 'No active PayPal settings'}, status=400)

            # Логируем входящие данные для отладки
            logger.info(f"PayPal webhook received: {request.data}")
            
            # Получаем данные из webhook
            data = request.data
            event_type = data.get('event_type')
            
            # Проверяем тип события
            if event_type not in ['PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.APPROVED']:
                logger.info(f"PayPal webhook: Ignoring event type {event_type}")
                return JsonResponse({'status': 'ignored'}, status=200)
            
            # Извлекаем информацию о заказе
            resource = data.get('resource', {})
            
            if event_type == 'PAYMENT.CAPTURE.COMPLETED':
                # Для завершенного платежа
                order_id = resource.get('custom_id') or resource.get('invoice_id')
                payment_id = resource.get('id')
            else:
                # Для одобренного заказа
                purchase_units = resource.get('purchase_units', [{}])
                order_id = purchase_units[0].get('reference_id') if purchase_units else None
                payment_id = resource.get('id')
            
            if not order_id:
                logger.error("PayPal webhook: No order_id found in webhook data")
                return JsonResponse({'error': 'No order_id found'}, status=400)
            
            logger.info(f"PayPal webhook: Processing order_id={order_id}, payment_id={payment_id}")
            
            # Обрабатываем успешный платеж
            _handle_successful_payment('paypal', order_id, payment_id, data)
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"PayPal webhook error: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)


class CreateFondyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            order_id = request.data.get('order_id')
            order = Order.objects.get(id=order_id, user=request.user)

            cfg = PaymentSettings.objects.filter(payment_system='fondy', is_active=True).first()
            if not cfg:
                return Response({'error': 'Fondy settings not found'}, status=400)

            client = FondyClient(cfg)
            fondy_data = client.create_payment(order)

            return Response({
                "data": fondy_data["data"],
                "signature": fondy_data["signature"],
                "payment_url": fondy_data["payment_url"]
            })

        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class FondyWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            raw_data = request.POST.get('data')
            signature = request.POST.get('signature')

            if not raw_data or not signature:
                logger.error("Fondy webhook: Missing data or signature")
                return JsonResponse({'error': 'Missing data or signature'}, status=400)

            try:
                decoded_data = json.loads(base64.b64decode(raw_data).decode())
                logger.info(f"Fondy webhook received: {decoded_data}")
            except Exception as e:
                logger.error(f"Fondy webhook: Invalid data format: {e}")
                return JsonResponse({'error': 'Invalid data format'}, status=400)

            # Получаем настройки Fondy
            cfg = PaymentSettings.objects.filter(
                payment_system='fondy', 
                is_active=True
            ).first()
            
            if not cfg:
                logger.error("Fondy webhook: No active Fondy settings found")
                return JsonResponse({'error': 'No active Fondy settings'}, status=400)

            # Проверяем подпись
            secret = cfg.secret_key if not cfg.sandbox else "test"
            sign_fields = ['order_id', 'merchant_id', 'amount', 'currency', 'order_status']
            sign_string = '|'.join([str(decoded_data.get(k, '')) for k in sign_fields]) + f"|{secret}"
            expected_signature = hashlib.sha1(sign_string.encode()).hexdigest()

            if signature != expected_signature:
                logger.error(f"Fondy webhook: Invalid signature. Expected: {expected_signature}, got: {signature}")
                return JsonResponse({'error': 'Invalid signature'}, status=400)

            # Проверяем статус заказа
            order_status = decoded_data.get('order_status')
            if order_status == 'approved':
                order_id = decoded_data.get('order_id')
                payment_id = decoded_data.get('payment_id')
                
                logger.info(f"Fondy webhook: Processing approved payment for order {order_id}")
                success = _handle_successful_payment('fondy', order_id, payment_id, decoded_data)
                
                if success:
                    logger.info(f"Successfully processed Fondy payment for order {order_id}")
                else:
                    logger.error(f"Failed to process Fondy payment for order {order_id}")
                    return JsonResponse({'error': 'Payment processing failed'}, status=500)
            else:
                logger.info(f"Fondy webhook: Ignoring order status {order_status}")

            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Fondy webhook error: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Internal server error'}, status=500)



class LiqPayWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            data_b64 = request.data.get('data')
            signature = request.data.get('signature')

            if not data_b64 or not signature:
                logger.error("LiqPay webhook: Missing data or signature")
                return Response({'error': 'Missing data or signature'}, status=400)

            # Получаем настройки LiqPay
            payment_settings = PaymentSettings.objects.filter(
                payment_system='liqpay', 
                is_active=True
            ).first()
            
            if not payment_settings:
                logger.error("LiqPay webhook: No active LiqPay settings found")
                return Response({'error': 'No active LiqPay settings'}, status=400)

            # Проверяем подпись
            secret = payment_settings.secret_key
            expected_signature = base64.b64encode(
                hashlib.sha1(f"{secret}{data_b64}{secret}".encode()).digest()
            ).decode()

            if signature != expected_signature:
                logger.error(f"LiqPay webhook: Invalid signature. Expected: {expected_signature}, got: {signature}")
                return Response({'error': 'Invalid signature'}, status=400)

            # Декодируем данные
            try:
                decoded_data = json.loads(base64.b64decode(data_b64).decode())
                logger.info(f"LiqPay webhook received: {decoded_data}")
            except Exception as e:
                logger.error(f"LiqPay webhook: Invalid data format: {e}")
                return Response({'error': 'Invalid data format'}, status=400)

            # Проверяем статус платежа
            status = decoded_data.get('status')
            if status == 'success':
                order_id = decoded_data.get('order_id')
                payment_id = decoded_data.get('payment_id')
                
                logger.info(f"LiqPay webhook: Processing successful payment for order {order_id}")
                success = _handle_successful_payment('liqpay', order_id, payment_id, decoded_data)
                
                if success:
                    logger.info(f"Successfully processed LiqPay payment for order {order_id}")
                else:
                    logger.error(f"Failed to process LiqPay payment for order {order_id}")
                    return Response({'error': 'Payment processing failed'}, status=500)
            else:
                logger.info(f"LiqPay webhook: Ignoring payment status {status}")

            return Response({'status': 'success'})
            
        except Exception as e:
            logger.error(f"LiqPay webhook error: {str(e)}", exc_info=True)
            return Response({'error': 'Internal server error'}, status=500)


class PortmoneWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        try:
            logger.info(f"Portmone webhook received: {request.data}")
            data = request.data
            
            # Получаем настройки Portmone
            payment_settings = PaymentSettings.objects.filter(
                payment_system='portmone', 
                is_active=True
            ).first()
            
            if not payment_settings:
                logger.error("Portmone webhook: No active Portmone settings found")
                return Response({'error': 'No active Portmone settings'}, status=400)
            
            # КРИТИЧНО: Валидация подписи Portmone
            secret = "test_secret" if payment_settings.sandbox else payment_settings.secret_key
            sign_data = '|'.join(str(data[k]) for k in sorted(data) if k != 'signature') + f"|{secret}"
            expected_signature = hashlib.sha1(sign_data.encode()).hexdigest()
            
            logger.info(f"Portmone signature validation:")
            logger.info(f"  Expected: {expected_signature}")
            logger.info(f"  Received: {data.get('signature')}")
            
            if data.get('signature') != expected_signature:
                logger.error("Portmone webhook: Invalid signature - potential security threat!")
                return Response({'error': 'Invalid signature'}, status=400)
            
            # Проверяем статус платежа
            status = data.get('status')
            if status == 'success':
                order_id = data.get('order_id')
                payment_id = data.get('payment_id')
                
                logger.info(f"Portmone webhook: Processing successful payment for order {order_id}")
                success = _handle_successful_payment('portmone', order_id, payment_id, data)
                
                if success:
                    logger.info(f"Successfully processed Portmone payment for order {order_id}")
                else:
                    logger.error(f"Failed to process Portmone payment for order {order_id}")
                    return Response({'error': 'Payment processing failed'}, status=500)
            else:
                logger.info(f"Portmone webhook: Ignoring payment status {status} for order {data.get('order_id')}")
            
            return Response({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Portmone webhook error: {str(e)}", exc_info=True)
            return Response({'error': 'Internal server error'}, status=500)


class CreatePortmonePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        order = get_object_or_404(Order, id=order_id, user=request.user)

        config = PaymentSettings.objects.filter(payment_system="portmone", is_active=True).first()
        if not config:
            return Response({"error": "Portmone is not configured"}, status=400)

        try:
            client = PortmoneClient(config)
            result = client.create_payment(order)

            return Response({
                "payment_id": result["payment_id"],
                "html_form": result["payment_html"]
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)