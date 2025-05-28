from django.urls import path
from rest_framework.routers import DefaultRouter
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
]

urlpatterns = api_urlpatterns + router.urls