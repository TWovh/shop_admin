#!/usr/bin/env python
"""
Скрипт для запуска тестов с coverage
"""
import os
import sys
import subprocess
from pathlib import Path

def run_command(command):
    """Выполнить команду и вернуть результат"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def main():
    """Основная функция"""
    print("🧪 Запуск тестов с coverage...")
    print("=" * 50)
    
    # Очищаем предыдущие данные coverage
    print("🗑️  Очищаем предыдущие данные coverage...")
    run_command("coverage erase")
    
    # Запускаем тесты с coverage
    print("🚀 Запускаем тесты...")
    success, stdout, stderr = run_command(
        "coverage run --source='.' manage.py test "
        "shop.tests.ModelTests "
        "shop.tests.SerializerTests "
        "shop.tests.CeleryTaskTests "
        "shop.tests.PaymentTests "
        "--settings=shopadmin.test_settings"
    )
    
    if success:
        print("✅ Тесты прошли успешно!")
        print(stdout)
    else:
        print("❌ Тесты не прошли!")
        print(stderr)
        return
    
    # Генерируем отчет
    print("\n📊 Генерируем отчет coverage...")
    success, stdout, stderr = run_command("coverage report")
    
    if success:
        print("📈 Отчет coverage:")
        print(stdout)
    else:
        print("❌ Ошибка при генерации отчета:")
        print(stderr)
    
    # Создаем HTML отчет
    print("\n🌐 Создаем HTML отчет...")
    success, stdout, stderr = run_command("coverage html")
    
    if success:
        print("✅ HTML отчет создан в папке htmlcov/")
        print("📁 Откройте htmlcov/index.html в браузере для просмотра")
    else:
        print("❌ Ошибка при создании HTML отчета:")
        print(stderr)
    
    print("\n" + "=" * 50)
    print("🎉 Завершено!")

if __name__ == "__main__":
    main() 