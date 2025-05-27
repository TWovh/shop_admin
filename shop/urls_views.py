from django.urls import path
from .views import (
    index,
    ProductListView,
    ProductDetailView,
    CategoryListView,
    CategoryDetailView,
    CartView,
    UpdateCartItemView,
    RemoveCartItemView,
    add_to_cart,
)

urlpatterns = [
    path('', index, name='index'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('cart/add/', add_to_cart, name='add-to-cart'),
    path('cart/item/<int:item_id>/update/', UpdateCartItemView.as_view(), name='cart-update'),
    path('cart/item/<int:item_id>/remove/', RemoveCartItemView.as_view(), name='cart-remove'),
]