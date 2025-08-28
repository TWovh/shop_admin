"""
Кэширование для приложения shop
"""
import json
import hashlib
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

# Время жизни кэша по умолчанию
DEFAULT_CACHE_TIMEOUT = 3600  # 1 час

# Ключи кэша
CACHE_KEYS = {
    'products': 'products:list',
    'categories': 'categories:list',
    'product_detail': 'product:detail:{id}',
    'user_orders': 'user:orders:{user_id}',
    'nova_poshta_cities': 'nova_poshta:cities:{search}',
    'nova_poshta_warehouses': 'nova_poshta:warehouses:{city_ref}',
    'payment_settings': 'payment:settings:{system}',
    'order_stats': 'order:stats:{date}',
    'user_cart': 'user:cart:{user_id}',
}


def cache_key_generator(prefix, *args, **kwargs):
    """
    Генератор ключей кэша
    """
    key_parts = [prefix]
    
    # Добавляем аргументы
    for arg in args:
        key_parts.append(str(arg))
    
    # Добавляем именованные аргументы
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    
    # Создаем хеш для длинных ключей
    key_string = ":".join(key_parts)
    if len(key_string) > 250:  # Redis ограничение
        return f"{prefix}:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    return key_string


def cache_products_list(products, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Кэширование списка товаров
    """
    key = CACHE_KEYS['products']
    cache.set(key, products, timeout)
    logger.info(f"Cached products list with key: {key}")


def get_cached_products_list():
    """
    Получение кэшированного списка товаров
    """
    key = CACHE_KEYS['products']
    return cache.get(key)


def cache_product_detail(product_id, product_data, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Кэширование детальной информации о товаре
    """
    key = CACHE_KEYS['product_detail'].format(id=product_id)
    cache.set(key, product_data, timeout)
    logger.info(f"Cached product detail for ID {product_id}")


def get_cached_product_detail(product_id):
    """
    Получение кэшированной информации о товаре
    """
    key = CACHE_KEYS['product_detail'].format(id=product_id)
    return cache.get(key)


def cache_user_orders(user_id, orders, timeout=1800):  # 30 минут
    """
    Кэширование заказов пользователя
    """
    key = CACHE_KEYS['user_orders'].format(user_id=user_id)
    cache.set(key, orders, timeout)
    logger.info(f"Cached orders for user {user_id}")


def get_cached_user_orders(user_id):
    """
    Получение кэшированных заказов пользователя
    """
    key = CACHE_KEYS['user_orders'].format(user_id=user_id)
    return cache.get(key)


def cache_nova_poshta_cities(search, cities, timeout=86400):  # 24 часа
    """
    Кэширование городов Nova Poshta
    """
    key = CACHE_KEYS['nova_poshta_cities'].format(search=search)
    cache.set(key, cities, timeout)
    logger.info(f"Cached Nova Poshta cities for search: {search}")


def get_cached_nova_poshta_cities(search):
    """
    Получение кэшированных городов Nova Poshta
    """
    key = CACHE_KEYS['nova_poshta_cities'].format(search=search)
    return cache.get(key)


def cache_nova_poshta_warehouses(city_ref, warehouses, timeout=86400):  # 24 часа
    """
    Кэширование отделений Nova Poshta
    """
    key = CACHE_KEYS['nova_poshta_warehouses'].format(city_ref=city_ref)
    cache.set(key, warehouses, timeout)
    logger.info(f"Cached Nova Poshta warehouses for city: {city_ref}")


def get_cached_nova_poshta_warehouses(city_ref):
    """
    Получение кэшированных отделений Nova Poshta
    """
    key = CACHE_KEYS['nova_poshta_warehouses'].format(city_ref=city_ref)
    return cache.get(key)


def cache_payment_settings(payment_system, settings_data, timeout=3600):  # 1 час
    """
    Кэширование настроек платежной системы
    """
    key = CACHE_KEYS['payment_settings'].format(system=payment_system)
    cache.set(key, settings_data, timeout)
    logger.info(f"Cached payment settings for {payment_system}")


def get_cached_payment_settings(payment_system):
    """
    Получение кэшированных настроек платежной системы
    """
    key = CACHE_KEYS['payment_settings'].format(system=payment_system)
    return cache.get(key)


def cache_order_stats(date, stats, timeout=3600):  # 1 час
    """
    Кэширование статистики заказов
    """
    key = CACHE_KEYS['order_stats'].format(date=date.strftime('%Y-%m-%d'))
    cache.set(key, stats, timeout)
    logger.info(f"Cached order stats for date: {date}")


def get_cached_order_stats(date):
    """
    Получение кэшированной статистики заказов
    """
    key = CACHE_KEYS['order_stats'].format(date=date.strftime('%Y-%m-%d'))
    return cache.get(key)


def cache_user_cart(user_id, cart_data, timeout=1800):  # 30 минут
    """
    Кэширование корзины пользователя
    """
    key = CACHE_KEYS['user_cart'].format(user_id=user_id)
    cache.set(key, cart_data, timeout)
    logger.info(f"Cached cart for user {user_id}")


def get_cached_user_cart(user_id):
    """
    Получение кэшированной корзины пользователя
    """
    key = CACHE_KEYS['user_cart'].format(user_id=user_id)
    return cache.get(key)


def invalidate_cache_pattern(pattern):
    """
    Инвалидация кэша по паттерну (только для Redis)
    """
    try:
        # Получаем все ключи по паттерну
        keys = cache.keys(pattern)
        if keys:
            cache.delete_many(keys)
            logger.info(f"Invalidated {len(keys)} cache keys with pattern: {pattern}")
    except Exception as e:
        logger.error(f"Error invalidating cache pattern {pattern}: {e}")


def invalidate_product_cache(product_id=None):
    """
    Инвалидация кэша товаров
    """
    if product_id:
        # Инвалидируем конкретный товар
        key = CACHE_KEYS['product_detail'].format(id=product_id)
        cache.delete(key)
        logger.info(f"Invalidated product cache for ID: {product_id}")
    
    # Инвалидируем список товаров
    cache.delete(CACHE_KEYS['products'])
    logger.info("Invalidated products list cache")


def invalidate_user_cache(user_id):
    """
    Инвалидация кэша пользователя
    """
    # Инвалидируем заказы пользователя
    key = CACHE_KEYS['user_orders'].format(user_id=user_id)
    cache.delete(key)
    
    # Инвалидируем корзину пользователя
    cart_key = CACHE_KEYS['user_cart'].format(user_id=user_id)
    cache.delete(cart_key)
    
    logger.info(f"Invalidated cache for user: {user_id}")


def cache_decorator(timeout=DEFAULT_CACHE_TIMEOUT, key_prefix=''):
    """
    Декоратор для кэширования функций
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Генерируем ключ кэша
            cache_key = cache_key_generator(
                f"{key_prefix}:{func.__name__}", 
                *args, 
                **kwargs
            )
            
            # Пытаемся получить из кэша
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Выполняем функцию
            result = func(*args, **kwargs)
            
            # Сохраняем в кэш
            cache.set(cache_key, result, timeout)
            logger.debug(f"Cached result for key: {cache_key}")
            
            return result
        return wrapper
    return decorator


# Примеры использования декоратора
@cache_decorator(timeout=3600, key_prefix='products')
def get_expensive_product_data(product_id):
    """
    Пример дорогой операции, которую стоит кэшировать
    """
    # Здесь может быть сложный запрос к БД или внешнему API
    pass


def get_cache_stats():
    """
    Получение статистики кэша (только для Redis)
    """
    try:
        info = cache.client.info()
        return {
            'used_memory': info.get('used_memory_human', 'N/A'),
            'connected_clients': info.get('connected_clients', 0),
            'total_commands_processed': info.get('total_commands_processed', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {} 