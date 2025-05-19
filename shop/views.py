from rest_framework import generics, permissions
from django.http import HttpResponse
from .serializers import ProductSerializer, CategorySerializer
from .cart_serializers import CartItemSerializer, AddToCartSerializer
from .models import Product, Category, Cart, CartItem
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from .serializers import OrderSerializer

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer

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
    cart, created = Cart.objects.get_or_create(user=request.user)
    serializer = CartItemSerializer(cart.items.all(), many=True)
    return Response({
        'items': serializer.data,
        'total_price': cart.total_price()
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    serializer = AddToCartSerializer(data=request.data)
    if serializer.is_valid():
        product = Product.objects.get(id=serializer.validated_data['product_id'])
        cart, created = Cart.objects.get_or_create(user=request.user)
        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': serializer.validated_data['quantity']}
        )
        if not created:
            item.quantity += serializer.validated_data['quantity']
            item.save()
        return Response({'status': 'success'})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def index(request):
    return render(request, 'index.html')

class OrderListCreateView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.orders.all()

    def perform_create(self, serializer):
        cart = self.request.user.cart
        order = cart.create_order(
            shipping_address=serializer.validated_data['shipping_address'],
            phone=serializer.validated_data['phone'],
            email=serializer.validated_data['email'],
            comments=serializer.validated_data.get('comments', '')
        )
        serializer.instance = order

