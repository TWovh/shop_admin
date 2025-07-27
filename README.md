# Интернет-магазин на Django
Поменяй вайткофиг, сеттингс, енв на фронте

Проект интернет-магазина с административной панелью, API и корзиной товаров.

## Основные возможности

- Управление товарами и категориями через админку
- REST API для интеграции с фронтендом
- Система корзины для зарегистрированных пользователей
- Загрузка изображений товаров

## Технологический стек

- Python 3.9+
- Django 5.2
- Django REST Framework
- PostgreSQL
- Docker (будет реализовано позже)

## Установка

1. Клонируйте репозиторий:
git clone https://github.com/TWovh/shopadmin.git

cd shopadmin

3. Создайте и активируйте виртуальное окружение:
python -m venv venv

source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

5. Установите зависимости:

pip install -r requirements.txt

4. Настройте бд в shopadmin/settings.py:

python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'shopdb',
        'USER': 'shopuser',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

5. Примените миграции:
python manage.py migrate


6. Создайте суперпользователя:
python manage.py createsuperuser

8. Запустите сервер: 
python manage.py runserver


9. API Endpoints
GET /api/products/ - список товаров

GET /api/products/<id>/ - детали товара

GET /api/categories/ - список категорий

GET /api/cart/ - просмотр корзины (требуется аутентификация)

POST /api/cart/add/ - добавление в корзину (требуется аутентификация)

10. Администрирование
Админка доступна по адресу /admin/. Возможности:

Управление товарами и категориями

Просмотр заказов

Управление пользователями

11. Развертывание в production
Установите PostgreSQL и настройте подключение
Установите DEBUG = False в settings.py
Настройте веб-сервер (Nginx + Gunicorn)

12. Для раздачи статики выполните:
python manage.py collectstatic



Этот README содержит:
1. Общее описание проекта
2. Инструкции по установке
3. Описание структуры проекта
4. Документацию по API
5. Информацию об администрировании
6. Рекомендации по деплою
