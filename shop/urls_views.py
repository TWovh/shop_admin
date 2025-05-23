from django.urls import path
from .views import (
    index,
    ProductListView,
    ProductDetailView,
    CategoryListView,
    CategoryDetailView,
    CartView
)

urlpatterns = [
    path('', index, name='index'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    path('cart/', CartView.as_view(), name='cart'),
]