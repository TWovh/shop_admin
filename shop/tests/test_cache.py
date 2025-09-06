"""
Тесты для системы кэширования
"""
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from shop.cache import (
    get_cached_products_list, cache_products_list,
    get_cached_product_detail, cache_product_detail,
    invalidate_product_cache
)
from shop.models import Product, Category

User = get_user_model()


class CacheTestCase(TestCase):
    """Базовый класс для тестов кэширования"""
    
    def setUp(self):
        cache.clear()
        
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category'
        )
        
        self.product = Product.objects.create(
            name='Тестовый товар',
            slug='test-product',
            category=self.category,
            price=100.00,
            stock=10,
            available=True
        )


class ProductsCacheTests(CacheTestCase):
    """Тесты кэширования списка товаров"""
    
    def test_cache_products_list(self):
        """Тест кэширования списка товаров"""
        products_data = [
            {
                'id': self.product.id,
                'name': self.product.name,
                'price': str(self.product.price)
            }
        ]
        
        cache_products_list(products_data)
        cached_data = get_cached_products_list()
        
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data, products_data)
    
    def test_get_cached_products_list_empty_cache(self):
        """Тест получения данных из пустого кэша"""
        cached_data = get_cached_products_list()
        self.assertIsNone(cached_data)


class ProductDetailCacheTests(CacheTestCase):
    """Тесты кэширования детальной информации о товаре"""
    
    def test_cache_product_detail(self):
        """Тест кэширования детальной информации о товаре"""
        product_data = {
            'id': self.product.id,
            'name': self.product.name,
            'price': str(self.product.price)
        }
        
        cache_product_detail(self.product.id, product_data)
        cached_data = get_cached_product_detail(self.product.id)
        
        self.assertIsNotNone(cached_data)
        self.assertEqual(cached_data, product_data)
    
    def test_get_cached_product_detail_empty_cache(self):
        """Тест получения данных из пустого кэша"""
        cached_data = get_cached_product_detail(999)
        self.assertIsNone(cached_data)


class ProductCacheInvalidationTests(CacheTestCase):
    """Тесты инвалидации кэша товаров"""
    
    def test_invalidate_product_cache(self):
        """Тест инвалидации кэша товара"""
        product_data = {'id': self.product.id, 'name': self.product.name}
        cache_product_detail(self.product.id, product_data)
        
        cached_data = get_cached_product_detail(self.product.id)
        self.assertIsNotNone(cached_data)
        
        invalidate_product_cache(self.product.id)
        
        cached_data = get_cached_product_detail(self.product.id)
        self.assertIsNone(cached_data)