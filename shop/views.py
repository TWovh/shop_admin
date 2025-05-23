from rest_framework import generics
from django.http import HttpResponse
from .serializers import ProductSerializer, CategorySerializer
from .cart_serializers import CartItemSerializer, AddToCartSerializer
from .models import Product, Category, Cart, CartItem
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from .serializers import OrderSerializer
from rest_framework import viewsets
from django.contrib.auth import login
from django.shortcuts import render, redirect
from .forms import UserRegistrationForm
from rest_framework.throttling import UserRateThrottle
from .permissions import IsAdmin, IsStaff, IsOwnerOrAdmin, CartThrottle
from django.core.cache import cache
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404


class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer

    def get_queryset(self):
        cache_key = 'available_products'
        queryset = cache.get(cache_key)
        if not queryset:
            queryset = Product.objects.filter(available=True)
            cache.set(cache_key, queryset, timeout=60 * 15)
        return queryset

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryDetailView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

def home(request):
    return HttpResponse("""
        <h1>Добро пожаловать в магазин</h1>
        <p>Доступные API endpoints:</p>
        <ul>
            <li><a href="/api/products/">Товары</a></li>
            <li><a href="/api/categories/">Категории</a></li>
            <li><a href="/admin/">Админка</a></li>
        </ul>
    """)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cart_detail(request):
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)

    serializer = CartItemSerializer(cart.items.all(), many=True)
    return Response({
        'items': serializer.data,
        'total_price': cart.total_price
    })

def index(request):
    products = Product.objects.filter(available=True)[:8]  # 8 последних доступных товаров
    return render(request, 'index.html', {'products': products})

class OrderListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    serializer_class = OrderSerializer
    throttle_classes = [UserRateThrottle]

    def get_queryset(self):
        return self.request.user.orders.all()

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



class CartView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [CartThrottle]

    def get(self, request):
        """Получение содержимого корзины (для API и HTML)"""
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.select_related('product').all()
        total_price = sum(item.total_price for item in cart_items)

        if request.accepted_renderer.format == 'html':
            return render(request, 'cart.html', {
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

    @action(detail=True, methods=['POST'])
    def update_item(self, request, item_id):
        """Обновление количества товара"""
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        quantity = int(request.data.get('quantity', 1))

        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()

        if request.accepted_renderer.format == 'html':
            return redirect('cart')
        return Response({'status': 'updated'})

    @action(detail=True, methods=['DELETE'])
    def remove_item(self, request, item_id):
        """Удаление товара из корзины"""
        cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
        cart_item.delete()

        if request.accepted_renderer.format == 'html':
            return redirect('cart')
        return Response({'status': 'removed'})

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
    return render(request, 'register.html', {'form': form})

class CartThrottle(UserRateThrottle):
    scope = 'cart'