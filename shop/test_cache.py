"""
Тестовый файл для демонстрации работы кэширования
"""
import time
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET"])
def test_cache_view(request):
    """
    Тестовая view для демонстрации кэширования
    """
    start_time = time.time()
    
    # Пытаемся получить из кэша
    cached_data = cache.get('test:expensive_operation')
    
    if cached_data:
        # Кэш попадание!
        response_time = (time.time() - start_time) * 1000
        logger.info(f"Cache HIT! Response time: {response_time:.2f}ms")
        
        return JsonResponse({
            'status': 'success',
            'data': cached_data,
            'cache': 'HIT',
            'response_time_ms': round(response_time, 2),
            'message': 'Данные получены из кэша!'
        })
    else:
        # Кэш промах - имитируем дорогую операцию
        time.sleep(0.5)  # Имитируем запрос к БД или внешнему API
        
        # Генерируем данные
        data = {
            'timestamp': time.time(),
            'message': 'Это дорогая операция, которая выполнилась',
            'items': [f'item_{i}' for i in range(10)]
        }
        
        # Сохраняем в кэш на 30 секунд
        cache.set('test:expensive_operation', data, timeout=30)
        
        response_time = (time.time() - start_time) * 1000
        logger.info(f"Cache MISS! Response time: {response_time:.2f}ms")
        
        return JsonResponse({
            'status': 'success',
            'data': data,
            'cache': 'MISS',
            'response_time_ms': round(response_time, 2),
            'message': 'Данные получены из БД/API и сохранены в кэш!'
        })


@csrf_exempt
@require_http_methods(["POST"])
def clear_test_cache(request):
    """
    Очистка тестового кэша
    """
    cache.delete('test:expensive_operation')
    
    return JsonResponse({
        'status': 'success',
        'message': 'Тестовый кэш очищен!'
    })


@csrf_exempt
@require_http_methods(["GET"])
def cache_stats_view(request):
    """
    Статистика кэша
    """
    try:
        # Пытаемся получить статистику Redis
        info = cache.client.info()
        stats = {
            'used_memory': info.get('used_memory_human', 'N/A'),
            'connected_clients': info.get('connected_clients', 0),
            'total_commands_processed': info.get('total_commands_processed', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
        }
        
        # Вычисляем hit rate
        total_requests = stats['keyspace_hits'] + stats['keyspace_misses']
        if total_requests > 0:
            hit_rate = (stats['keyspace_hits'] / total_requests) * 100
        else:
            hit_rate = 0
            
        stats['hit_rate_percent'] = round(hit_rate, 2)
        
        return JsonResponse({
            'status': 'success',
            'cache_backend': 'Redis',
            'stats': stats
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'cache_backend': 'Unknown',
            'message': f'Не удалось получить статистику: {str(e)}'
        })


def simulate_expensive_operation():
    """
    Имитация дорогой операции (запрос к БД, внешний API и т.д.)
    """
    time.sleep(0.3)  # Имитируем задержку
    return {
        'result': 'expensive_data',
        'timestamp': time.time(),
        'processing_time': 0.3
    }


@cache_decorator(timeout=60, key_prefix='demo')
def cached_expensive_operation(operation_type):
    """
    Пример использования декоратора кэширования
    """
    logger.info(f"Выполняется дорогая операция: {operation_type}")
    return simulate_expensive_operation()


# Импортируем декоратор из cache.py
from .cache import cache_decorator 