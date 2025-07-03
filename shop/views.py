from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from rest_framework.request import Request

from . import serializers
from .models import Product, Order, OrderItem
from rest_framework import generics
from .serializers import ProductSerializer, CategorySerializer
from .cart_serializers import CartItemSerializer, AddToCartSerializer
from .models import Category, Cart, CartItem
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import OrderSerializer
from django.contrib.auth import login
from django.shortcuts import render, redirect
from .forms import UserRegistrationForm
from rest_framework.throttling import UserRateThrottle
from .permissions import IsStaff, IsOwnerOrAdmin, CartThrottle
from django.core.cache import cache
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.contrib import messages
from .utils import get_nova_poshta_api_key
from django.http import JsonResponse
import requests


class ProductListView(ListView):
    model = Product
    template_name = 'admin/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        cache_key = 'available_products'
        queryset = cache.get(cache_key)
        if not queryset:
            queryset = Product.objects.filter(available=True)
            cache.set(cache_key, queryset, timeout=60 * 15)
        return queryset
class ProductDetailView(generics.RetrieveAPIView):
    lookup_field = 'id'
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer

class ProductDetailHTMLView(DetailView):
    model = Product
    template_name = 'shop/product_detail.html'
    context_object_name = 'product'


class CategoryProductListView(DetailView):
    model = Category
    template_name = 'shop/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = self.object.products.filter(available=True)
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

class CategoryDetailHTMLView(DetailView):
    model = Category
    template_name = 'shop/category_detail_info.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = self.object.products.filter(available=True)
        return context

def index(request):
    try:
        products = Product.objects.filter(available=True).order_by('-created')[:8]
        return render(request, 'shop/index.html', {'products': products})
    except Exception as e:
        # Логирование ошибки для отладки
        print(f"Error in index view: {str(e)}")
        return render(request, 'shop/index.html', {'products': []})



class OrderCreateSerializer(serializers.Serializer):
    address = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    city = serializers.CharField(required=True)
    delivery_type = serializers.ChoiceField(choices=[('prepaid', 'Оплата онлайн'), ('cod', 'Наложенный платеж')], default='prepaid')
    comments = serializers.CharField(required=False, allow_blank=True, default='')



class OrderListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = OrderSerializer
    throttle_classes = [UserRateThrottle]

    queryset = Order.objects.none()  # Чтобы CBV работал без ошибок

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        cart = get_object_or_404(Cart, user=self.request.user)
        if not cart.items.exists():
            raise ValidationError("Корзина пуста")

        # Валидируем входящие данные через сериализатор
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
            order.status = 'new'

        order.save()
        return order

    def handle_exception(self, exc):
        from django.core.exceptions import ValidationError as DjangoValidationError

        if isinstance(exc, (Cart.DoesNotExist, ValidationError, DjangoValidationError)):
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return super().handle_exception(exc)



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

        serializer = CartItemSerializer(cart_items, many=True)
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

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsStaff]
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'slug'



def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'USER'  # Автоматически назначаем роль
            user.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})


def add_to_cart(request, product_id=None): #delete
    if not request.user.is_authenticated:
        messages.error(request, "Для добавления в корзину войдите в систему")
        return redirect('login')

    product = get_object_or_404(Product, id=product_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )

    if not created:
        item.quantity += 1
        item.save()

    messages.success(request, f"Товар {product.name} добавлен в корзину")
    return redirect('shop:product-list')

@login_required
def start_checkout_view(request):
    cart = Cart.objects.prefetch_related('items__product').filter(user=request.user).first()
    if not cart or not cart.items.exists():
        return render(request, 'admin/checkout.html', {
            'error': 'Ваша корзина пуста',
        })

    # Создаем заказ
    order = Order.objects.create(
        user=request.user,
        city='',
        address='',
        phone=request.user.profile.phone if hasattr(request.user, 'profile') else '',
        email=request.user.email,
        status='new',
        payment_status='unpaid',
    )

    # Копируем товары из корзины
    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price=item.product.price
        )

    order.update_total_price()
    cart.items.all().delete()

    # Переход на форму доставки и оплаты
    return redirect('shop:checkout', order_id=order.pk)


@login_required
def checkout_view(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)

    if request.method == 'POST':
        city_name = request.POST.get('city')
        city_ref = request.POST.get('city_ref')
        warehouse_name = request.POST.get('warehouse_name')
        warehouse_ref = request.POST.get('warehouse_ref')
        payment_method = request.POST.get('payment_method')
        delivery_type = request.POST.get('delivery_type')

        order.city = city_name
        order.city_ref = city_ref
        order.address = f"Отделение НП: {warehouse_name}"
        order.warehouse_ref = warehouse_ref
        order.delivery_type = delivery_type
        order.payment_status = 'unpaid'
        order.save()

        # Редирект на оплату по выбранной системе
        if delivery_type == 'cod':
            return redirect('/orders/')
        elif payment_method == 'stripe':
            return redirect(f'/payment/stripe/{order.pk}/')
        elif payment_method == 'paypal':
            return redirect(f'/payment/paypal/{order.pk}/')
        elif payment_method == 'fondy':
            return redirect(f'/payment/fondy/{order.pk}/')
        elif payment_method == 'liqpay':
            return redirect(f'/payment/liqpay/{order.pk}/')

        return redirect('/orders/')  # или другой путь, если ЛК есть

    return render(request, 'admin/checkout.html', {
        'order': order,
        'cart_items': order.order_items.all(),
        'cart_total': order.total_price,
    })

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


def payment_stripe(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'payment/stripe.html', {'order': order})

def payment_paypal(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'payment/paypal.html', {'order': order})

def payment_fondy(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'payment/fondy.html', {'order': order})

def payment_liqpay(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'payment/liqpay.html', {'order': order})