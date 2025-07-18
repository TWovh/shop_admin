from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Product, Order, OrderItem
from rest_framework import generics
from .serializers import ProductSerializer, CategorySerializer, UserSerializer, RegisterSerializer, \
    CurrentUserSerializer, OrderCreateSerializer
from .serializers import CartItemSerializer, AddToCartSerializer
from .models import Category, Cart, CartItem
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .serializers import OrderSerializer
from django.shortcuts import render, redirect
from rest_framework.throttling import UserRateThrottle
from .permissions import IsStaff, IsOwnerOrAdmin, CartThrottle
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .utils import get_nova_poshta_api_key
from django.http import JsonResponse, HttpRequest
import requests
from shop.admin_dashboard import admin_site

User = get_user_model()


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class CategoryListHTMLView(ListView):
    model = Category
    template_name = 'shop/category_list.html'
    context_object_name = 'categories'


class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CategoryDetailView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'


class CategoryDetailHTMLView(DetailView):
    model = Category
    template_name = 'shop/category_detail_info.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = self.object.products.filter(available=True)
        return context


def statistics_view(request: HttpRequest):
    return admin_site.statistics_view(request)

def get_product_price(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return JsonResponse({'price': str(product.price)})


class OrderListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    throttle_classes = [UserRateThrottle]

    queryset = Order.objects.none()  # Чтобы CBV работал без ошибок

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        cart = get_object_or_404(Cart, user=self.request.user)
        if not cart.items.exists():
            raise ValidationError("Корзина пуста")

        order_data_serializer = OrderCreateSerializer(data=self.request.data)
        order_data_serializer.is_valid(raise_exception=True)
        validated_data = order_data_serializer.validated_data

        order = cart.create_order(
            shipping_address=validated_data['address'],
            phone=validated_data['phone'],
            email=validated_data['email'],
            comments=validated_data.get('comments', ''),
        )
        order.city = validated_data['city']
        order.delivery_type = validated_data.get('delivery_type', 'prepaid')

        if order.delivery_type == 'cod':
            order.payment_status = 'unpaid'
            order.status = 'processing'
        else:
            order.payment_status = 'unpaid'
            order.status = 'pending'

        order.save()
        return order

    def create(self, request, *args, **kwargs):
        # Создаём заказ через perform_create
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = self.perform_create(serializer)

        # Сериализуем созданный заказ для ответа
        response_serializer = self.get_serializer(order)

        headers = self.get_success_headers(response_serializer.data)
        return Response({
            'order': response_serializer.data,
            'order_id': order.id,
            'message': 'Заказ успешно создан'
        }, status=status.HTTP_201_CREATED, headers=headers)

    def handle_exception(self, exc):
        from django.core.exceptions import ValidationError as DjangoValidationError

        if isinstance(exc, (Cart.DoesNotExist, ValidationError, DjangoValidationError)):
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return super().handle_exception(exc)




class LatestOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        latest_order = Order.objects.filter(user=request.user).order_by('-created_at').first()
        if latest_order:
            return Response({'id': latest_order.id})
        return Response({'error': 'Заказ не найден'}, status=404)

# апи для наложки
class MarkCodPaidAPIView(APIView):
    permission_classes = [IsStaff]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, delivery_type='cod')
        except Order.DoesNotExist:
            return Response({"detail": "Заказ не найден или не наложка."}, status=404)

        if order.status == 'completed':
            return Response({"detail": "Заказ уже завершён."}, status=400)

        order.payment_status = 'paid'
        order.status = 'completed'
        order.save()
        return Response({"detail": f"Заказ #{pk} отмечен как оплачен."})


class MarkCodRejectedAPIView(APIView):
    permission_classes = [IsStaff]

    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk, delivery_type='cod')
        except Order.DoesNotExist:
            return Response({"detail": "Заказ не найден или не наложка."}, status=404)

        if order.status == 'cancelled':
            return Response({"detail": "Заказ уже отменён."}, status=400)

        order.payment_status = 'refunded'
        order.status = 'cancelled'
        order.save()
        return Response({"detail": f"Заказ #{pk} отменён как не оплаченный."})


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'shop/orders.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created')


class OrderDetailAPIView(generics.RetrieveAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = 'order_id'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Получение содержимого корзины (для API и HTML)"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.select_related('product').all()
        total_price = sum(item.total_price for item in cart_items)

        if request.accepted_renderer.format == 'html':
            return render(request, 'admin/cart.html', {
                'cart_items': cart_items,
                'total_price': total_price
            })

        serializer = CartItemSerializer(cart_items, many=True, context={'request': request})
        return Response({
            'items': serializer.data,
            'total_price': total_price
        })


class AddToCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data['quantity']

        product = get_object_or_404(Product, id=product_id, available=True)
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.add_product(product, quantity)
        return Response({'message': 'Товар добавлен в корзину'}, status=status.HTTP_201_CREATED)


class CartItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)

        quantity = request.data.get('quantity')
        if quantity is None:
            return Response({'error': 'Поле quantity обязательно'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity < 1 or quantity > 100:
                raise ValueError()
        except ValueError:
            return Response({'error': 'Количество должно быть числом от 1 до 100'}, status=status.HTTP_400_BAD_REQUEST)

        item.quantity = quantity
        item.save()
        return Response({'message': 'Количество обновлено'})

    def delete(self, request, item_id):
        cart = get_object_or_404(Cart, user=request.user)
        item = get_object_or_404(CartItem, id=item_id, cart=cart)
        item.delete()
        return Response({'message': 'Товар удалён из корзины'}, status=status.HTTP_204_NO_CONTENT)


class ClearCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        cart.clear()
        return Response({'message': 'Корзина очищена'})


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            })
        else:
            return Response({'detail': 'Неверный email или пароль'}, status=status.HTTP_401_UNAUTHORIZED)





def get_cities(request):
    api_key = get_nova_poshta_api_key()
    if not api_key:
        return JsonResponse({"error": "API ключ не настроен"}, status=400)

    search = request.GET.get("search", "")
    payload = {
        "apiKey": api_key,
        "modelName": "Address",
        "calledMethod": "getCities",
        "methodProperties": {
            "FindByString": search,
        }
    }
    response = requests.post("https://api.novaposhta.ua/v2.0/json/", json=payload)
    return JsonResponse(response.json())


def get_warehouses(request):
    from .utils import get_nova_poshta_api_key
    api_key = get_nova_poshta_api_key()
    if not api_key:
        return JsonResponse({"error": "API ключ не настроен"}, status=400)

    city_ref = request.GET.get("city_ref")
    if not city_ref:
        return JsonResponse({"error": "Не передан city_ref"}, status=400)

    payload = {
        "apiKey": api_key,
        "modelName": "Address",
        "calledMethod": "getWarehouses",
        "methodProperties": {
            "CityRef": city_ref,
            "Language": "UA"
        }
    }

    response = requests.post("https://api.novaposhta.ua/v2.0/json/", json=payload)
    return JsonResponse(response.json())

