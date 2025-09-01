#!/usr/bin/env python
"""
Скрипт для запуска тестов с разными опциями
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(command, description=""):
    """Запуск команды с выводом"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"{'='*60}")
    print(f"Команда: {command}")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    end_time = time.time()
    
    print(f"Время выполнения: {end_time - start_time:.2f} секунд")
    print(f"Код возврата: {result.returncode}")
    
    if result.stdout:
        print("\n📤 STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("\n❌ STDERR:")
        print(result.stderr)
    
    if result.returncode == 0:
        print("✅ Команда выполнена успешно!")
    else:
        print("❌ Команда завершилась с ошибкой!")
    
    return result.returncode == 0

def main():
    """Основная функция"""
    print("🧪 Система тестирования Django проекта")
    print("=" * 60)
    
    # Проверяем что мы в правильной директории
    if not Path("manage.py").exists():
        print("❌ Файл manage.py не найден. Убедитесь что вы в корневой папке проекта.")
        return
    
    # Проверяем что виртуальное окружение активировано
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Виртуальное окружение не активировано!")
        print("   Активируйте его: venv\\Scripts\\activate")
        return
    
    while True:
        print("\n📋 Выберите тип тестов:")
        print("1. 🔍 Все тесты")
        print("2. 🏗️  Тесты моделей")
        print("3. 🔌 Тесты API")
        print("4. 💾 Тесты кэширования")
        print("5. 🔄 Тесты Celery задач")
        print("6. 💳 Тесты платежей")
        print("7. 📦 Тесты Nova Poshta")
        print("8. ⚡ Тесты производительности")
        print("9. 🔒 Тесты безопасности")
        print("10. 🔗 Интеграционные тесты")
        print("11. 📊 Тесты с покрытием кода")
        print("12. 🐛 Тесты с отладкой")
        print("13. 🚀 Быстрые тесты")
        print("0. ❌ Выход")
        
        choice = input("\nВведите номер (0-13): ").strip()
        
        if choice == "0":
            print("👋 До свидания!")
            break
        
        elif choice == "1":
            # Все тесты
            success = run_command(
                "python manage.py test --settings=shopadmin.test_settings",
                "Запуск всех тестов"
            )
        
        elif choice == "2":
            # Тесты моделей
            success = run_command(
                "python manage.py test shop.tests.ModelTests --settings=shopadmin.test_settings",
                "Тесты моделей"
            )
        
        elif choice == "3":
            # Тесты API
            success = run_command(
                "python manage.py test shop.tests.APITests --settings=shopadmin.test_settings",
                "Тесты API"
            )
        
        elif choice == "4":
            # Тесты кэширования
            success = run_command(
                "python manage.py test shop.tests.CacheTests --settings=shopadmin.test_settings",
                "Тесты кэширования"
            )
        
        elif choice == "5":
            # Тесты Celery задач
            success = run_command(
                "python manage.py test shop.tests.CeleryTaskTests --settings=shopadmin.test_settings",
                "Тесты Celery задач"
            )
        
        elif choice == "6":
            # Тесты платежей
            success = run_command(
                "python manage.py test shop.tests.PaymentTests --settings=shopadmin.test_settings",
                "Тесты платежных систем"
            )
        
        elif choice == "7":
            # Тесты Nova Poshta
            success = run_command(
                "python manage.py test shop.tests.NovaPoshtaTests --settings=shopadmin.test_settings",
                "Тесты Nova Poshta"
            )
        
        elif choice == "8":
            # Тесты производительности
            success = run_command(
                "python manage.py test shop.tests.PerformanceTests --settings=shopadmin.test_settings",
                "Тесты производительности"
            )
        
        elif choice == "9":
            # Тесты безопасности
            success = run_command(
                "python manage.py test shop.tests.SecurityTests --settings=shopadmin.test_settings",
                "Тесты безопасности"
            )
        
        elif choice == "10":
            # Интеграционные тесты
            success = run_command(
                "python manage.py test shop.tests.IntegrationTests --settings=shopadmin.test_settings",
                "Интеграционные тесты"
            )
        
        elif choice == "11":
            # Тесты с покрытием кода
            print("\n📊 Установка coverage...")
            subprocess.run("pip install coverage", shell=True)
            
            success = run_command(
                "coverage run --source='.' manage.py test --settings=shopadmin.test_settings",
                "Тесты с покрытием кода"
            )
            
            if success:
                run_command("coverage report", "Отчет о покрытии кода")
                run_command("coverage html", "Создание HTML отчета")
                print("📁 HTML отчет создан в папке htmlcov/")
        
        elif choice == "12":
            # Тесты с отладкой
            success = run_command(
                "python manage.py test --settings=shopadmin.test_settings --verbosity=3",
                "Тесты с подробным выводом"
            )
        
        elif choice == "13":
            # Быстрые тесты
            success = run_command(
                "python manage.py test shop.tests.ModelTests shop.tests.APITests --settings=shopadmin.test_settings --parallel",
                "Быстрые тесты (параллельно)"
            )
        
        else:
            print("❌ Неверный выбор. Попробуйте снова.")
            continue
        
        if success:
            print("\n🎉 Тесты прошли успешно!")
        else:
            print("\n💥 Тесты завершились с ошибками!")
        
        # Спрашиваем продолжить или выйти
        continue_choice = input("\nПродолжить тестирование? (y/n): ").strip().lower()
        if continue_choice not in ['y', 'yes', 'да', 'д']:
            print("👋 До свидания!")
            break

def run_specific_test():
    """Запуск конкретного теста"""
    print("\n🎯 Запуск конкретного теста")
    print("Примеры:")
    print("  shop.tests.ModelTests.test_product_creation")
    print("  shop.tests.APITests.test_products_list_api")
    print("  shop.tests.CacheTests.test_cache_miss_and_hit")
    
    test_name = input("\nВведите имя теста: ").strip()
    
    if test_name:
        command = f"python manage.py test {test_name} --settings=shopadmin.test_settings"
        run_command(command, f"Запуск теста: {test_name}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc() 