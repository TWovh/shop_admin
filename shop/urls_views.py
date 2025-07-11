from django.urls import path
from . import views
from .views import (
    index,
    CartItemDetailView,
    CartView, checkout_view,
    OrderListView,
    CategoryListHTMLView,
    CategoryDetailHTMLView,
    start_checkout_view,
    statistics_view, get_product_price,
)

app_name = 'shop'
urlpatterns = [
    path('', index, name='index'),
    path("admin/statistics/", statistics_view, name="statistics"),
    path('categories/', CategoryListHTMLView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailHTMLView.as_view(), name='category-detail'),
    path('orders/', OrderListView.as_view(), name='orders'),
    path('cart/', CartView.as_view(), name='cart'),
    path('checkout/start/', start_checkout_view, name='start_checkout'),
    path('checkout/<int:order_id>/', checkout_view, name='checkout'),
    path('get-product-price/<int:pk>/', get_product_price, name='get_product_price'),
    path('cart/items/<int:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),

]