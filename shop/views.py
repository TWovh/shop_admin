from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from .models import Product, Order
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



class OrderListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = OrderSerializer
    throttle_classes = [UserRateThrottle]

    queryset = Order.objects.none()  # нужно, чтобы CBV работал без ошибок

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        cart = self.request.user.cart
        if not cart.items.exists():
            raise ValidationError("Корзина пуста")

        order = cart.create_order(
            shipping_address=serializer.validated_data['shipping_address'],
            phone=serializer.validated_data['phone'],
            email=serializer.validated_data['email'],
            comments=serializer.validated_data.get('comments', '')
        )
        serializer.instance = order
    def handle_exception(self, exc):
        if isinstance(exc, (Cart.DoesNotExist, ValidationError)):
            return Response(
                {'error': str(exc)},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().handle_exception(exc)


class OrderListView(LoginRequiredMixin, ListView):
    model = Order
    template_name = 'shop/orders.html'
    context_object_name = 'orders'

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created')



class CartView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CartThrottle]

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

    def post(self, request):
        """Добавление товара в корзину"""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = get_object_or_404(Product, id=serializer.validated_data['product_id'])
        if not product.available:
            return Response(
                {'error': 'Товар недоступен'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart, _ = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': serializer.validated_data['quantity']}
        )

        if not created:
            item.quantity += serializer.validated_data['quantity']
            item.save()

        if request.accepted_renderer.format == 'html':
            return redirect('cart')
        return Response({'status': 'success'})


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


def add_to_cart(request, product_id=None):
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

class UpdateCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)

        quantity = request.data.get('quantity')
        try:
            quantity = int(quantity)
            if quantity < 1 or quantity > 100:
                raise ValueError()
        except (TypeError, ValueError):
            return Response({'error': 'Неверное количество'}, status=400)

        item.quantity = quantity
        item.save()

        return Response({'status': 'updated', 'quantity': item.quantity, 'total_price': item.total_price})

class RemoveCartItemView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()

        cart = Cart.objects.get(user=request.user)
        cart_total = cart.total_price

        return Response({'status': 'removed', 'cart_total': float(cart_total)}, status=status.HTTP_200_OK)

@login_required
def checkout_view(request):
    cart = Cart.objects.prefetch_related('items__product').filter(user=request.user).first()
    if not cart or not cart.items.exists():
        return render(request, 'admin/checkout.html', {
            'error': 'Ваша корзина пуста',
        })

    cart_items = cart.items.all()
    cart_total = sum(item.total_price for item in cart_items)

    return render(request, 'admin/checkout.html', {
        'cart_items': cart_items,
        'cart_total': cart_total,
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