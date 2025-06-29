from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views
from .views_payments import CreatePaymentView, StripeWebhookView
from .views import (
    ProductViewSet,
    CategoryViewSet,
    CartView,
    OrderListCreateAPIView,
    CategoryDetailView,

)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='api-product')  # Измените basename
router.register(r'categories', CategoryViewSet, basename='api-category')

api_urlpatterns = [
    path('cart/', CartView.as_view(), name='api-cart'),
    path('cart/items/<int:item_id>/', CartView.as_view(), name='api-cart-item-detail'),
    path('api/orders/', OrderListCreateAPIView.as_view(), name='order-list-api'),
    path('api/categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail-api'),
    path('orders/<int:order_id>/pay/', CreatePaymentView.as_view(), name='create-payment'),
    path('webhooks/stripe/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path("api/np/cities/", views.get_cities, name="np_get_cities"),
    path("api/np/warehouses/", views.get_warehouses, name="np_get_warehouses"),

]

urlpatterns = api_urlpatterns + router.urls