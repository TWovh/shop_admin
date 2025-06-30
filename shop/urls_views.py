from django.urls import path
from . import views
from .views import (
    index,
    ProductListView,
    UpdateCartItemView,
    RemoveCartItemView,
    CategoryProductListView,
    ProductDetailHTMLView,
    add_to_cart, CartView, checkout_view,
    OrderListView,
    CategoryListHTMLView,
    CategoryDetailHTMLView,
    start_checkout_view,
)

app_name = 'shop'
urlpatterns = [
    path('', index, name='index'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/<slug:slug>/', ProductDetailHTMLView.as_view(), name='product-detail'),
    path('category/<slug:slug>/', CategoryProductListView.as_view(), name='category-products'),
    path('categories/', CategoryListHTMLView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailHTMLView.as_view(), name='category-detail'),
    path('orders/', OrderListView.as_view(), name='orders'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add-to-cart'),
    path('cart/', CartView.as_view(), name='cart'),
    path('checkout/start/', start_checkout_view, name='start_checkout'),
    path('checkout/<int:order_id>/', checkout_view, name='checkout'),
    path('cart/item/<int:item_id>/update/', UpdateCartItemView.as_view(), name='cart-update'),
    path('cart/item/<int:item_id>/remove/', RemoveCartItemView.as_view(), name='cart-remove'),
    path('payment/stripe/<int:order_id>/', views.payment_stripe, name='payment_stripe'),
    path('payment/paypal/<int:order_id>/', views.payment_paypal, name='payment_paypal'),
    path('payment/fondy/<int:order_id>/', views.payment_fondy, name='payment_fondy'),
    path('payment/liqpay/<int:order_id>/', views.payment_liqpay, name='payment_liqpay'),
]