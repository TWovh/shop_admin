from django.urls import path, include
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
    MarkCodPaidAPIView, LatestOrderView,
)
from .views_payments import CreatePaymentView, PaymentMethodsView, PaymentOptionsAPIView, \
    ActivePaymentSystemsView, ActivePaymentMethodsAPIView, stripe_webhook, PayPalWebhookView, FondyWebhookView, \
    LiqPayWebhookView, PortmoneWebhookView, StripePublicKeyView

from . import views

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='api-product')
router.register(r'categories', CategoryViewSet, basename='api-category')

api_urlpatterns = [
    path('', include(router.urls)),
    #корзина пользователя
    path('cart/', CartView.as_view(), name='api-cart'),  # GET корзина пользователя
    path('cart/add/', AddToCartView.as_view(), name='api-cart-add'),  # POST добавить товар
    path('cart/items/<int:item_id>/', CartItemDetailView.as_view(), name='api-cart-item-detail'),
    path('cart/clear/', ClearCartView.as_view(), name='api-cart-clear'),

    # Заказы
    path('orders/', OrderListCreateAPIView.as_view(), name='order-list-create'),
    path('orders/<int:order_id>/', OrderDetailAPIView.as_view(), name='order-detail'),
    path('orders/latest/', LatestOrderView.as_view(), name='latest-order'),

    # Оплата
    path('orders/<int:order_id>/pay/', CreatePaymentView.as_view(), name='create-payment'),
    path('payment-methods/', PaymentMethodsView.as_view(), name='payment-methods'),
    path('payments/options/', PaymentOptionsAPIView.as_view(), name='payment-options'),#для фронта
    path('api/payment-systems/', ActivePaymentSystemsView.as_view(), name='active-payment-systems'), #только актив
    path('payment-methods/active/', ActivePaymentMethodsAPIView.as_view(), name='active-payment-methods'),
    path('stripe/webhook/', stripe_webhook, name='stripe-webhook'),
    path('paypal/', PayPalWebhookView.as_view(), name='paypal'),
    path('stripe/public-key/', StripePublicKeyView.as_view(), name='stripe-public-key'),
    path('fondy/', FondyWebhookView.as_view(), name='fondy'),
    path('liqpay/', LiqPayWebhookView.as_view(), name='liqpay'),
    path('portmone/', PortmoneWebhookView.as_view(), name='portmone'),



    # Новая Почта
    path("np/cities/", views.get_cities, name="np_get_cities"),
    path("np/warehouses/", views.get_warehouses, name="np_get_warehouses"),
    path('orders/<int:pk>/mark-cod-paid/', MarkCodPaidAPIView.as_view(), name='mark_cod_paid'),
    path('orders/<int:pk>/mark-cod-rejected/', MarkCodRejectedAPIView.as_view(), name='mark_cod_rejected'),


    #Авторизация
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('user/me/', CurrentUserView.as_view(), name='user_me'),
    path('auth/login/', LoginView.as_view(), name='login'),
]

urlpatterns = api_urlpatterns + router.urls