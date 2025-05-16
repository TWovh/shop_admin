from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('api/products/', views.ProductListView.as_view(), name='product_list'),
    path('api/products/<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('api/categories/', views.CategoryListView.as_view(), name='category_list'),
    path('api/categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),
]