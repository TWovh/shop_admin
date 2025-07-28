from django.urls import path
from .views import (
    CartItemDetailView,
    CartView,
    statistics_view, get_product_price,
)

app_name = 'shop'
urlpatterns = [
    path("admin/statistics/", statistics_view, name="statistics"),
    path('cart/', CartView.as_view(), name='cart'),
    path('get-product-price/<int:pk>/', get_product_price, name='get_product_price'),
    path('cart/items/<int:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),

]