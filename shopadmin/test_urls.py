"""
URL'ы для тестирования
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

# Импортируем views для тестирования (без проблемных импортов)
from shop.test_views import (
    ProductViewSet, CategoryViewSet, CartView, CartItemDetailView, 
    AddToCartView, OrderListCreateAPIView, OrderDetailAPIView, 
    ClearCartView, RegisterView, CurrentUserView, LoginView
)
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

api_urlpatterns = [
    # Продукты и категории
    path('products/', ProductViewSet.as_view({'get': 'list'}), name='api-product-list'),
    path('products/<int:pk>/', ProductViewSet.as_view({'get': 'retrieve'}), name='api-product-detail'),
    path('categories/', CategoryViewSet.as_view({'get': 'list'}), name='api-category-list'),
    path('categories/<int:pk>/', CategoryViewSet.as_view({'get': 'retrieve'}), name='api-category-detail'),
    
    # Корзина пользователя
    path('cart/', CartView.as_view({'get': 'list'}), name='api-cart'),
    path('cart/add/', AddToCartView.as_view({'post': 'create'}), name='api-cart-add'),
    path('cart/items/<int:item_id>/', CartItemDetailView.as_view({'delete': 'destroy'}), name='api-cart-item-detail'),
    path('cart/clear/', ClearCartView.as_view({'post': 'create'}), name='api-cart-clear'),

    # Заказы
    path('orders/', OrderListCreateAPIView.as_view({'get': 'list', 'post': 'create'}), name='order-list-create'),
    path('orders/<int:order_id>/', OrderDetailAPIView.as_view({'get': 'retrieve'}), name='order-detail'),

    # Авторизация
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view({'post': 'create'}), name='register'),
    path('user/me/', CurrentUserView.as_view({'get': 'list'}), name='user_me'),
    path('auth/login/', LoginView.as_view({'post': 'create'}), name='login'),
    
    # Webhook'и (заглушки для тестов)
    path('webhooks/stripe/', lambda request: HttpResponse('OK'), name='stripe-webhook'),
    path('webhooks/paypal/', lambda request: HttpResponse('OK'), name='paypal-webhook'),
    path('webhooks/fondy/', lambda request: HttpResponse('OK'), name='fondy-webhook'),
    path('webhooks/liqpay/', lambda request: HttpResponse('OK'), name='liqpay-webhook'),
    path('webhooks/portmone/', lambda request: HttpResponse('OK'), name='portmone-webhook'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_urlpatterns)),
] 