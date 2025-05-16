from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    # URL для продуктов
    path('', views.ProductListView.as_view(), name='product_list'),  # Список продуктов
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),  # Детали продукта

    # URL для категорий
    path('categories/', views.CategoryListView.as_view(), name='category_list'),  # Список категорий
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),  # Детали категории
]