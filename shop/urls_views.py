from django.urls import path
from .views import (
    index,
    ProductListView,
    ProductDetailView,
    CategoryListView,
    CategoryDetailView,
    UpdateCartItemView,
    RemoveCartItemView,
    CategoryProductListView,
    ProductDetailHTMLView,
    add_to_cart, CartView, checkout_view,
    OrderListView,
)

app_name = 'shop'
urlpatterns = [
    path('', index, name='index'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/<slug:slug>/', ProductDetailHTMLView.as_view(), name='product-detail'),
    path('api/products/<int:pk>/', ProductDetailView.as_view(), name='product-detail-api'),    path('category/<slug:slug>/', CategoryProductListView.as_view(), name='category-products'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('orders/', OrderListView.as_view(), name='orders'),
    path('cart/add/<int:product_id>/', add_to_cart, name='add-to-cart'),
    path('cart/', CartView.as_view(), name='cart'),
    path('checkout/', checkout_view, name='checkout'),
    path('cart/item/<int:item_id>/update/', UpdateCartItemView.as_view(), name='cart-update'),
    path('cart/item/<int:item_id>/remove/', RemoveCartItemView.as_view(), name='cart-remove'),
]