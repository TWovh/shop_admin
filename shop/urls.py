from django.urls import path
from . import views
from .views import cart_detail, add_to_cart

app_name = 'shop'

urlpatterns = [
    # URL для продуктов
    path('', views.ProductListView.as_view(), name='product_list'),  # Список
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product_detail'),  # Детали

    # URL для категорий
    path('categories/', views.CategoryListView.as_view(), name='category_list'),  # Список категорий
    path('categories/<int:pk>/', views.CategoryDetailView.as_view(), name='category_detail'),  # Детали категории
    path('cart/', cart_detail, name='cart'),
    path('cart/add/', add_to_cart, name='add_to_cart'),
]