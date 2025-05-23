from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    ProductViewSet,
    CategoryViewSet,
    CartView,
    OrderListCreateView
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')

urlpatterns = [
    path('cart/', CartView.as_view(), name='cart-api'),
    path('cart/items/<int:item_id>/', CartView.as_view(), name='cart-item-detail'),
    path('orders/', OrderListCreateView.as_view(), name='order-list'),
] + router.urls