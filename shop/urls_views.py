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
)

app_name = 'shop'
urlpatterns = [
    path('', index, name='index'),
    path('categories/', CategoryListHTMLView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailHTMLView.as_view(), name='category-detail'),
    path('orders/', OrderListView.as_view(), name='orders'),
    path('cart/', CartView.as_view(), name='cart'),
    path('checkout/start/', start_checkout_view, name='start_checkout'),
    path('checkout/<int:order_id>/', checkout_view, name='checkout'),
    path('cart/items/<int:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),
    path('payment/stripe/<int:order_id>/', views.payment_stripe, name='payment_stripe'),
    path('payment/paypal/<int:order_id>/', views.payment_paypal, name='payment_paypal'),
    path('payment/fondy/<int:order_id>/', views.payment_fondy, name='payment_fondy'),
    path('payment/liqpay/<int:order_id>/', views.payment_liqpay, name='payment_liqpay'),
]