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
from .models import PaymentSettings, Payment, Order, NovaPoshtaSettings
from .permissions import IsAdminOrUser
import logging
from .serializers import PaymentSettingsSerializer, PaymentMethodSerializer, PaymentDetailSerializer
from .utils import send_payment_confirmation_email
from .views import create_ttn

logger = logging.getLogger(__name__)

class CreatePaymentView(APIView):
    permission_classes = [IsAdminOrUser]


    def post(self, request, order_id):
        print(
            f"User: {request.user.email}, role: {getattr(request.user, 'role', None)}, user_role: {getattr(request, 'user_role', None)}")
        print("=== CreatePaymentView ===")
        print("request.user:", request.user)
        print("request.user.is_authenticated:", request.user.is_authenticated)
        print("request.user.role:", getattr(request.user, 'role', None))
        print("request.user_role (from middleware):", getattr(request, 'user_role', None))

        payment_system = request.data.get('payment_system')

        try:
            order = Order.objects.get(id=order_id, user=request.user)
            print(f"Order.user: {order.user}, request.user: {request.user}")
        except Order.DoesNotExist:
            return Response({'error': 'Заказ не найден'}, status=404)

        if order.user != request.user:
            return Response({'error': 'Нет доступа к заказу'}, status=403)

        print(f"Order status: {order.status}")

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
            try:
                client = StripeClient(payment_settings)
                session_id, url = client.create_checkout(order)

                Payment.objects.create(
                    order=order,
                    user=self.request.user,
                    amount=order.total_price,
                    payment_system=system,
                    external_id=session_id,
                    raw_response={},
                    status='pending'
                )

                return Response({'session_id': session_id})

            except Exception as e:
                print("🔥 Ошибка Stripe:", str(e))
                import traceback
                traceback.print_exc()
                return Response({'error': str(e)}, status=500)
        elif system == 'paypal':
            client = PayPalClient(payment_settings)
            ext_id, url, raw = client.create_order(order)
        elif system == 'fondy':
            client = FondyClient(payment_settings)
            ext_id, url, raw = client.create_payment(order)
        elif system == 'liqpay':
            client = LiqPayClient(payment_settings)
            data_b64, sign = client.create_form(order)
            raw = {'data': data_b64, 'signature': sign}
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
    from .models import Order, Payment

    try:
        order = Order.objects.get(id=order_id)

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

        # Обновим статусы заказа
        if order.payment_status != 'paid':
            order.payment_status = 'paid'
            if order.status == 'pending':
                order.status = 'processing'
            order.save()
            send_payment_confirmation_email(order, payment)
            from .models import NovaPoshtaSettings
            from .views import create_ttn

            settings_qs = NovaPoshtaSettings.objects.filter(is_active=True)
            if settings_qs.count() == 1:
                settings = settings_qs.get()
                if settings.auto_create_ttn and order.delivery_method == 'nova_poshta':
                    result = create_ttn(order, settings=settings)
                    if not result.get("success"):
                        print(f"[Nova Poshta] Ошибка создания ТТН для заказа #{order.id}: {result.get('message')}")


    except Exception as e:
        import traceback
        logger.error(f"❌ Ошибка обработки оплаты {system}: {e}")
        traceback.print_exc()


@csrf_exempt
def stripe_webhook(request):
    import stripe
    payment_settings = PaymentSettings.objects.filter(payment_system='stripe', is_active=True).first()
    if not payment_settings:
        return JsonResponse({'error': 'No active Stripe settings'}, status=400)

    webhook_secret = payment_settings.webhook_secret
    stripe.api_key = payment_settings.secret_key

    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        print("❌ Ошибка Stripe Webhook:", str(e))
        return JsonResponse({'error': str(e)}, status=400)

    print("✅ Stripe webhook пришёл:", event['type'])

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        metadata = session.get('metadata', {})

        print("📦 session.metadata:", metadata)

        order_id = metadata.get('order_id')
        if not order_id:
            print("⚠️ Нет order_id в metadata!")
            return JsonResponse({'error': 'Missing order_id'}, status=400)

        from .models import Order
        try:
            order = Order.objects.get(id=order_id)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

        _handle_successful_payment('stripe', order_id, session['id'], session)

    return HttpResponse(status=200)

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
        data = request.data
        payment_settings = PaymentSettings.objects.filter(payment_system='paypal', is_active=True).first()
        if not payment_settings:
            return JsonResponse({'error': 'No active PayPal settings'}, status=400)

        order_id = data.get('resource', {}).get('purchase_units', [{}])[0].get('reference_id')
        payment_id = data.get('resource', {}).get('id')

        _handle_successful_payment('paypal', order_id, payment_id, data)
        return Response({'status': 'success'})


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
        raw_data = request.POST.get('data')
        signature = request.POST.get('signature')

        if not raw_data or not signature:
            return JsonResponse({'error': 'Missing data or signature'}, status=400)

        try:
            decoded_data = json.loads(base64.b64decode(raw_data).decode())
        except Exception:
            return JsonResponse({'error': 'Invalid data format'}, status=400)

        cfg = PaymentSettings.objects.filter(payment_system='fondy', is_active=True).first()
        if not cfg:
            return JsonResponse({'error': 'No active Fondy settings'}, status=400)

        secret = cfg.secret_key if not cfg.sandbox else "test"

        sign_fields = ['order_id', 'merchant_id', 'amount', 'currency', 'order_status']
        sign_string = '|'.join([str(decoded_data.get(k, '')) for k in sign_fields]) + f"|{secret}"
        expected_signature = hashlib.sha1(sign_string.encode()).hexdigest()

        if signature != expected_signature:
            return JsonResponse({'error': 'Invalid signature'}, status=400)

        if decoded_data.get('order_status') == 'approved':
            _handle_successful_payment('fondy', decoded_data['order_id'], decoded_data.get('payment_id'), decoded_data)

        return JsonResponse({'status': 'success'})



class LiqPayWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        data_b64 = request.data.get('data')
        signature = request.data.get('signature')

        if not data_b64 or not signature:
            return Response({'error': 'Missing data or signature'}, status=400)

        payment_settings = PaymentSettings.objects.filter(payment_system='liqpay', is_active=True).first()
        if not payment_settings:
            return Response({'error': 'No active LiqPay settings'}, status=400)

        secret = payment_settings.secret_key
        expected_signature = base64.b64encode(
            hashlib.sha1(f"{secret}{data_b64}{secret}".encode()).digest()
        ).decode()

        if signature != expected_signature:
            logger.warning("❌ Неверная подпись в webhook от LiqPay")
            return Response({'error': 'Invalid signature'}, status=400)

        try:
            decoded_data = json.loads(base64.b64decode(data_b64).decode())
            logger.info(f"✅ LiqPay webhook data: {decoded_data}")
        except Exception as e:
            logger.error(f"Ошибка при декодировании LiqPay data: {e}")
            return Response({'error': 'Invalid data payload'}, status=400)

        order_id = decoded_data.get('order_id')
        payment_id = decoded_data.get('payment_id')
        status = decoded_data.get('status')

        if not order_id or not payment_id:
            return Response({'error': 'Missing order_id or payment_id'}, status=400)

        # Считаем успешными как 'success', так и 'sandbox' (в тестах)
        if status in ['success', 'sandbox']:
            _handle_successful_payment('liqpay', order_id, payment_id, decoded_data)

        return Response({'status': 'ok'})


class PortmoneWebhookView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        logger.info("Portmone webhook called")

        data = request.data
        logger.info(f"Incoming data: {data}")

        payment_settings = PaymentSettings.objects.filter(payment_system='portmone', is_active=True).first()
        if not payment_settings:
            logger.error("No active Portmone settings found")
            return JsonResponse({'error': 'No active Portmone settings'}, status=400)

        secret = "test_secret" if payment_settings.sandbox else payment_settings.secret_key
        sign_data = '|'.join(str(data[k]) for k in sorted(data) if k != 'signature') + f"|{secret}"
        expected_signature = hashlib.sha1(sign_data.encode()).hexdigest()

        logger.info(f"Expected signature: {expected_signature}")
        logger.info(f"Received signature: {data.get('signature')}")

        if data.get('signature') != expected_signature:
            logger.warning("Invalid signature")
            return Response({'error': 'Invalid signature'}, status=400)

        if data.get('status') == 'success':
            logger.info("Successful payment received, calling _handle_successful_payment")
            _handle_successful_payment(
                system='portmone',
                order_id=data.get('order_id'),
                external_id=data.get('payment_id'),
                raw_data=data
            )
        else:
            logger.info(f"Unhandled payment status: {data.get('status')}")

        return Response({'status': 'success'})


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