"""
Views для тестирования (без импорта admin_dashboard)
"""
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Product, Category, Cart, CartItem, Order, OrderItem
from .serializers import ProductSerializer, CategorySerializer, CartItemSerializer, OrderSerializer

User = get_user_model()


class CartSerializer(serializers.ModelSerializer):
    """Сериализатор для корзины"""
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price']
        read_only_fields = ['user', 'total_price']
    
    def get_total_price(self, obj):
        return str(obj.total_price)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для продуктов"""
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer
    
    def get_queryset(self):
        queryset = Product.objects.filter(available=True)
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__slug=category)
        return queryset


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для категорий"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class CartView(viewsets.ViewSet):
    """View для корзины"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)


class CartItemDetailView(viewsets.ViewSet):
    """View для элементов корзины"""
    permission_classes = [IsAuthenticated]
    
    def destroy(self, request, item_id=None):
        try:
            item = CartItem.objects.get(id=item_id, cart__user=request.user)
            item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CartItem.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class AddToCartView(viewsets.ViewSet):
    """View для добавления товара в корзину"""
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity', 1)
        
        try:
            product = Product.objects.get(id=product_id, available=True)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Товар не найден'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if quantity <= 0:
            return Response(
                {'error': 'Количество должно быть больше 0'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart.add_product(product, quantity)
        
        return Response({'message': 'Товар добавлен в корзину'}, status=status.HTTP_201_CREATED)


class ClearCartView(viewsets.ViewSet):
    """View для очистки корзины"""
    permission_classes = [IsAuthenticated]
    
    def create(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response({'message': 'Корзина очищена'}, status=status.HTTP_200_OK)


class OrderListCreateAPIView(viewsets.ViewSet):
    """View для создания и получения заказов"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        orders = Order.objects.filter(user=request.user)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    def create(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        if not cart.items.exists():
            return Response(
                {'error': 'Корзина пуста'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Создаем заказ
        order = Order.objects.create(
            user=request.user,
            email=request.data.get('email'),
            phone=request.data.get('phone'),
            address=request.data.get('address'),
            city=request.data.get('city'),
            total_price=cart.total_price,
            status='pending',
            payment_status='unpaid'
        )
        
        # Создаем элементы заказа
        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
        
        # Очищаем корзину
        cart.items.all().delete()
        
        serializer = OrderSerializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderDetailAPIView(viewsets.ViewSet):
    """View для получения детальной информации о заказе"""
    permission_classes = [IsAuthenticated]
    
    def retrieve(self, request, order_id=None):
        try:
            order = Order.objects.get(id=order_id, user=request.user)
            serializer = OrderSerializer(order)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class RegisterView(viewsets.ViewSet):
    """View для регистрации пользователя"""
    
    def create(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Пользователь с таким email уже существует'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        return Response({
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        }, status=status.HTTP_201_CREATED)


class CurrentUserView(viewsets.ViewSet):
    """View для получения информации о текущем пользователе"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        return Response({
            'email': request.user.email,
            'first_name': request.user.first_name,
            'last_name': request.user.last_name
        })


class LoginView(viewsets.ViewSet):
    """View для входа пользователя"""
    
    def create(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        user = authenticate(email=email, password=password)
        if user:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            })
        else:
            return Response(
                {'error': 'Неверные учетные данные'}, 
                status=status.HTTP_401_UNAUTHORIZED
            ) 