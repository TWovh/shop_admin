#!/usr/bin/env python
"""
Демонстрационный скрипт для показа работы кэширования
"""
import requests
import time
import json

BASE_URL = "http://localhost:8000/api"

def test_cache_performance():
    """
    Тестирование производительности кэша
    """
    print("🚀 Демонстрация работы кэширования")
    print("=" * 50)
    
    # Первый запрос (кэш промах)
    print("\n1️⃣ Первый запрос (Cache MISS):")
    start_time = time.time()
    response1 = requests.get(f"{BASE_URL}/test/cache/")
    time1 = (time.time() - start_time) * 1000
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"   ⏱️  Время ответа: {data1['response_time_ms']}ms")
        print(f"   📊 Статус кэша: {data1['cache']}")
        print(f"   💬 Сообщение: {data1['message']}")
    else:
        print(f"   ❌ Ошибка: {response1.status_code}")
        return
    
    # Второй запрос (кэш попадание)
    print("\n2️⃣ Второй запрос (Cache HIT):")
    start_time = time.time()
    response2 = requests.get(f"{BASE_URL}/test/cache/")
    time2 = (time.time() - start_time) * 1000
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"   ⏱️  Время ответа: {data2['response_time_ms']}ms")
        print(f"   📊 Статус кэша: {data2['cache']}")
        print(f"   💬 Сообщение: {data2['message']}")
    else:
        print(f"   ❌ Ошибка: {response2.status_code}")
        return
    
    # Третий запрос (кэш попадание)
    print("\n3️⃣ Третий запрос (Cache HIT):")
    start_time = time.time()
    response3 = requests.get(f"{BASE_URL}/test/cache/")
    time3 = (time.time() - start_time) * 1000
    
    if response3.status_code == 200:
        data3 = response3.json()
        print(f"   ⏱️  Время ответа: {data3['response_time_ms']}ms")
        print(f"   📊 Статус кэша: {data3['cache']}")
        print(f"   💬 Сообщение: {data3['message']}")
    else:
        print(f"   ❌ Ошибка: {response3.status_code}")
        return
    
    # Статистика
    print("\n📈 Статистика производительности:")
    print(f"   🐌 Первый запрос: {data1['response_time_ms']}ms (Cache MISS)")
    print(f"   ⚡ Второй запрос: {data2['response_time_ms']}ms (Cache HIT)")
    print(f"   ⚡ Третий запрос: {data3['response_time_ms']}ms (Cache HIT)")
    
    improvement = data1['response_time_ms'] / data2['response_time_ms']
    print(f"   🚀 Ускорение: в {improvement:.1f} раз быстрее!")


def test_cache_clear():
    """
    Тестирование очистки кэша
    """
    print("\n🧹 Тестирование очистки кэша:")
    print("=" * 30)
    
    # Очищаем кэш
    response = requests.post(f"{BASE_URL}/test/cache/clear/")
    if response.status_code == 200:
        print("   ✅ Кэш очищен")
    else:
        print(f"   ❌ Ошибка очистки: {response.status_code}")
        return
    
    # Делаем запрос после очистки
    print("\n🔄 Запрос после очистки кэша:")
    start_time = time.time()
    response = requests.get(f"{BASE_URL}/test/cache/")
    time_taken = (time.time() - start_time) * 1000
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ⏱️  Время ответа: {data['response_time_ms']}ms")
        print(f"   📊 Статус кэша: {data['cache']}")
        print(f"   💬 Сообщение: {data['message']}")
    else:
        print(f"   ❌ Ошибка: {response.status_code}")


def test_cache_stats():
    """
    Тестирование статистики кэша
    """
    print("\n📊 Статистика кэша:")
    print("=" * 20)
    
    response = requests.get(f"{BASE_URL}/test/cache/stats/")
    if response.status_code == 200:
        data = response.json()
        print(f"   🔧 Backend: {data['cache_backend']}")
        if 'stats' in data:
            stats = data['stats']
            print(f"   💾 Использовано памяти: {stats.get('used_memory', 'N/A')}")
            print(f"   👥 Подключенных клиентов: {stats.get('connected_clients', 0)}")
            print(f"   📈 Hit rate: {stats.get('hit_rate_percent', 0)}%")
            print(f"   ✅ Попадания в кэш: {stats.get('keyspace_hits', 0)}")
            print(f"   ❌ Промахи кэша: {stats.get('keyspace_misses', 0)}")
    else:
        print(f"   ❌ Ошибка получения статистики: {response.status_code}")


def test_products_cache():
    """
    Тестирование кэширования товаров
    """
    print("\n🛍️ Тестирование кэширования товаров:")
    print("=" * 40)
    
    # Первый запрос товаров
    print("\n1️⃣ Первый запрос товаров:")
    start_time = time.time()
    response1 = requests.get(f"{BASE_URL}/products/")
    time1 = (time.time() - start_time) * 1000
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"   ⏱️  Время ответа: {time1:.2f}ms")
        print(f"   📦 Количество товаров: {len(data1)}")
    else:
        print(f"   ❌ Ошибка: {response1.status_code}")
        return
    
    # Второй запрос товаров
    print("\n2️⃣ Второй запрос товаров:")
    start_time = time.time()
    response2 = requests.get(f"{BASE_URL}/products/")
    time2 = (time.time() - start_time) * 1000
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"   ⏱️  Время ответа: {time2:.2f}ms")
        print(f"   📦 Количество товаров: {len(data2)}")
    else:
        print(f"   ❌ Ошибка: {response2.status_code}")
        return
    
    # Статистика
    if time1 > 0:
        improvement = time1 / time2
        print(f"\n🚀 Ускорение: в {improvement:.1f} раз быстрее!")


if __name__ == "__main__":
    try:
        # Проверяем, что сервер запущен
        response = requests.get(f"{BASE_URL}/test/cache/", timeout=5)
        if response.status_code != 200:
            print("❌ Сервер не отвечает. Убедитесь, что Django сервер запущен на http://localhost:8000")
            exit(1)
        
        # Запускаем демонстрацию
        test_cache_performance()
        test_cache_clear()
        test_cache_stats()
        test_products_cache()
        
        print("\n🎉 Демонстрация завершена!")
        print("\n💡 Что мы увидели:")
        print("   • Первый запрос медленный (Cache MISS)")
        print("   • Последующие запросы быстрые (Cache HIT)")
        print("   • Кэш можно очищать")
        print("   • Статистика показывает эффективность кэша")
        
    except requests.exceptions.ConnectionError:
        print("❌ Не удалось подключиться к серверу.")
        print("   Убедитесь, что Django сервер запущен:")
        print("   python manage.py runserver")
    except Exception as e:
        print(f"❌ Ошибка: {e}") 