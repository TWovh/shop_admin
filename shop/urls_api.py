from django.urls import path, include
from django.views.decorators.csrf import csrf_exempt
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    ProductViewSet,
    CategoryViewSet,
    CartView,
    CartItemDetailView,
    AddToCartView,
    OrderListCreateAPIView,
    OrderDetailAPIView,
    ClearCartView,
    RegisterView,
    CurrentUserView,
    LoginView,
    MarkCodRejectedAPIView,
    MarkCodPaidAPIView, LatestOrderView, DashboardOverviewView, DashboardProfileUpdateView, DashboardOrderListView,
    DashboardOrderDetailView, DashboardOrderPayView, DashboardOrderCancelView, SendPasswordResetEmailView,
    ConfirmPasswordResetView, ChangePasswordView,
)
from .views_payments import CreatePaymentView, PaymentMethodsView, PaymentOptionsAPIView, \
    ActivePaymentSystemsView, ActivePaymentMethodsAPIView, stripe_webhook, PayPalWebhookView, FondyWebhookView, \
    LiqPayWebhookView, PortmoneWebhookView, StripePublicKeyView, CreateFondyPaymentView, CreatePortmonePaymentView

from . import views
from .test_cache import test_cache_view, clear_test_cache, cache_stats_view

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='api-product')
router.register(r'categories', CategoryViewSet, basename='api-category')

api_urlpatterns = [
    path('', include(router.urls)),
    
    # Корзина пользователя
    path('cart/', CartView.as_view(), name='api-cart'),
    path('cart/add/', AddToCartView.as_view(), name='api-cart-add'),
    path('cart/items/<int:item_id>/', CartItemDetailView.as_view(), name='api-cart-item-detail'),
    path('cart/clear/', ClearCartView.as_view(), name='api-cart-clear'),

    # Заказы
    path('orders/', OrderListCreateAPIView.as_view(), name='order-list-create'),
    path('orders/<int:order_id>/', OrderDetailAPIView.as_view(), name='order-detail'),
    path('orders/latest/', LatestOrderView.as_view(), name='latest-order'),
    path('orders/<int:pk>/mark-cod-paid/', MarkCodPaidAPIView.as_view(), name='mark_cod_paid'),
    path('orders/<int:pk>/mark-cod-rejected/', MarkCodRejectedAPIView.as_view(), name='mark_cod_rejected'),

    # Оплата
    path('orders/<int:order_id>/pay/', CreatePaymentView.as_view(), name='create-payment'),
    path('payment-methods/', PaymentMethodsView.as_view(), name='payment-methods'),
    path('payments/options/', PaymentOptionsAPIView.as_view(), name='payment-options'),
    path('payment-systems/', ActivePaymentSystemsView.as_view(), name='active-payment-systems'),
    path('payment-methods/active/', ActivePaymentMethodsAPIView.as_view(), name='active-payment-methods'),
    path('stripe/public-key/', StripePublicKeyView.as_view(), name='stripe-public-key'),
    
    # Webhook'и (без CSRF защиты)
    path('webhooks/stripe/', csrf_exempt(stripe_webhook), name='stripe-webhook'),
    path('webhooks/paypal/', csrf_exempt(PayPalWebhookView.as_view()), name='paypal-webhook'),
    path('webhooks/fondy/', csrf_exempt(FondyWebhookView.as_view()), name='fondy-webhook'),
    path('webhooks/liqpay/', csrf_exempt(LiqPayWebhookView.as_view()), name='liqpay-webhook'),
    path('webhooks/portmone/', csrf_exempt(PortmoneWebhookView.as_view()), name='portmone-webhook'),
    
    # Создание платежей
    path('fondy/create/', CreateFondyPaymentView.as_view(), name='fondy-create'),
    path('portmone/create/', CreatePortmonePaymentView.as_view(), name='portmone-create'),

    # Личный кабинет
    path('dashboard/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('dashboard/profile/', DashboardProfileUpdateView.as_view(), name='dashboard-profile-update'),
    path('dashboard/orders/', DashboardOrderListView.as_view(), name='dashboard-orders'),
    path('dashboard/orders/<int:pk>/', DashboardOrderDetailView.as_view(), name='dashboard-order-detail'),
    path('dashboard/orders/<int:pk>/pay/', DashboardOrderPayView.as_view(), name='dashboard-order-pay'),
    path('dashboard/orders/<int:pk>/cancel/', DashboardOrderCancelView.as_view(), name='dashboard-order-cancel'),
    
    # Сброс пароля
    path('password-reset/', SendPasswordResetEmailView.as_view(), name='password-reset'),
    path('password-reset/confirm/', ConfirmPasswordResetView.as_view(), name='password-reset-confirm'),
    path('auth/password/change/', ChangePasswordView.as_view(), name='password-change'),

    # Новая Почта
    path('np/cities/', views.get_cities, name='np_get_cities'),
    path('np/warehouses/', views.get_warehouses, name='np_get_warehouses'),
    path('np-autocomplete/cities/', views.CityAutocomplete.as_view(), name='np_city_autocomplete'),
    path('np-autocomplete/warehouses/', views.WarehouseAutocomplete.as_view(), name='np_warehouse_autocomplete'),

    # Авторизация
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('user/me/', CurrentUserView.as_view(), name='user_me'),
    path('auth/login/', LoginView.as_view(), name='login'),
    
    # Тестовые URL для демонстрации кэширования
    path('test/cache/', test_cache_view, name='test-cache'),
    path('test/cache/clear/', clear_test_cache, name='clear-test-cache'),
    path('test/cache/stats/', cache_stats_view, name='cache-stats'),
]

urlpatterns = api_urlpatterns + router.urls