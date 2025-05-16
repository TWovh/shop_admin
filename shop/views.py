from rest_framework import generics
from .models import Product, Category
from .serializers import ProductSerializer, CategorySerializer
from django.http import HttpResponse

class ProductListView(generics.ListAPIView):
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer

class ProductDetailView(generics.RetrieveAPIView):
    queryset = Product.objects.filter(available=True)
    serializer_class = ProductSerializer

class CategoryListView(generics.ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CategoryDetailView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

from django.http import HttpResponse

def home(request):
    return HttpResponse("""
        <h1>Добро пожаловать в магазин</h1>
        <p>Доступные API endpoints:</p>
        <ul>
            <li><a href="/api/products/">Товары</a></li>
            <li><a href="/api/categories/">Категории</a></li>
            <li><a href="/admin/">Админка</a></li>
        </ul>
    """)