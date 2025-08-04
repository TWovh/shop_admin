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
    MarkCodPaidAPIView, LatestOrderView, DashboardOverviewView, DashboardProfileUpdateView, DashboardOrderListView,
    DashboardOrderDetailView, DashboardOrderPayView, DashboardOrderCancelView, SendPasswordResetEmailView,
    ConfirmPasswordResetView, ChangePasswordView,
)
from .views_payments import CreatePaymentView, PaymentMethodsView, PaymentOptionsAPIView, \
    ActivePaymentSystemsView, ActivePaymentMethodsAPIView, stripe_webhook, PayPalWebhookView, FondyWebhookView, \
    LiqPayWebhookView, PortmoneWebhookView, StripePublicKeyView, CreateFondyPaymentView, CreatePortmonePaymentView

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
    path('orders/<int:pk>/mark-cod-paid/', MarkCodPaidAPIView.as_view(), name='mark_cod_paid'),
    path('orders/<int:pk>/mark-cod-rejected/', MarkCodRejectedAPIView.as_view(), name='mark_cod_rejected'),

    # Оплата
    path('orders/<int:order_id>/pay/', CreatePaymentView.as_view(), name='create-payment'),
    path('payment-methods/', PaymentMethodsView.as_view(), name='payment-methods'),
    path('payments/options/', PaymentOptionsAPIView.as_view(), name='payment-options'),#для фронта
    path('payment-systems/', ActivePaymentSystemsView.as_view(), name='active-payment-systems'), #только актив
    path('payment-methods/active/', ActivePaymentMethodsAPIView.as_view(), name='active-payment-methods'),
    path('stripe/webhook/', stripe_webhook, name='stripe-webhook'),
    path('paypal/', PayPalWebhookView.as_view(), name='paypal'),
    path('stripe/public-key/', StripePublicKeyView.as_view(), name='stripe-public-key'),
    path('fondy/webhook', FondyWebhookView.as_view(), name='fondy-webhook'),
    path('fondy/create/', CreateFondyPaymentView.as_view(), name='fondy-create'),
    path('liqpay/', LiqPayWebhookView.as_view(), name='liqpay'),
    path('portmone/', PortmoneWebhookView.as_view(), name='portmone-webhook'),
    path("portmone/create/", CreatePortmonePaymentView.as_view(), name="portmone-create"),


    # Личный кабинет
    path('dashboard/', DashboardOverviewView.as_view(), name='dashboard-overview'),
    path('dashboard/profile/', DashboardProfileUpdateView.as_view(), name='dashboard-profile-update'),
    path('dashboard/orders/', DashboardOrderListView.as_view(), name='dashboard-orders'),
    path('dashboard/orders/<int:pk>/', DashboardOrderDetailView.as_view(), name='dashboard-order-detail'),
    path('dashboard/orders/<int:pk>/pay/', DashboardOrderPayView.as_view(), name='dashboard-order-pay'),
    path('dashboard/orders/<int:pk>/cancel/', DashboardOrderCancelView.as_view(), name='dashboard-order-cancel'),
    path('password-reset/', SendPasswordResetEmailView.as_view()),
    path('password-reset/confirm/', ConfirmPasswordResetView.as_view()),
    path("auth/password/change/", ChangePasswordView.as_view()),


    # Новая Почта
    path("np/cities/", views.get_cities, name="np_get_cities"),
    path("np/warehouses/", views.get_warehouses, name="np_get_warehouses"),
    path("np-autocomplete/cities/", views.CityAutocomplete.as_view(), name="np_city_autocomplete"),
    path("np-autocomplete/warehouses/", views.WarehouseAutocomplete.as_view(), name="np_warehouse_autocomplete"),



    #Авторизация
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('user/me/', CurrentUserView.as_view(), name='user_me'),
    path('auth/login/', LoginView.as_view(), name='login'),
]

urlpatterns = api_urlpatterns + router.urls