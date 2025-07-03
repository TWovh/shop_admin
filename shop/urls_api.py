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
    ClearCartView, RegisterView, CurrentUserView, LoginView,
)
from .views_payments import CreatePaymentView, StripeWebhookView
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

    # Оплата
    path('orders/<int:order_id>/pay/', CreatePaymentView.as_view(), name='create-payment'),
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),

    # Новая Почта
    path("np/cities/", views.get_cities, name="np_get_cities"),
    path("np/warehouses/", views.get_warehouses, name="np_get_warehouses"),

    #Авторизация
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/user/me/', CurrentUserView.as_view(), name='user_me'),
    path('api/login/', LoginView.as_view(), name='login'),
]

urlpatterns = api_urlpatterns + router.urls