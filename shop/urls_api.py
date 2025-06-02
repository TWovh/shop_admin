from django.urls import path
from rest_framework.routers import DefaultRouter
from .views_payments import CreatePaymentView, PaymentWebhookView
from .views import (
    ProductViewSet,
    CategoryViewSet,
    CartView,
    OrderListCreateView
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='api-product')  # Измените basename
router.register(r'categories', CategoryViewSet, basename='api-category')

api_urlpatterns = [
    path('cart/', CartView.as_view(), name='api-cart'),
    path('cart/items/<int:item_id>/', CartView.as_view(), name='api-cart-item-detail'),
    path('orders/', OrderListCreateView.as_view(), name='api-order-list'),
    path('orders/<int:order_id>/pay/', CreatePaymentView.as_view(), name='create-payment'),
    path('webhooks/stripe/', PaymentWebhookView.as_view(), name='stripe-webhook'),

]

urlpatterns = api_urlpatterns + router.urls