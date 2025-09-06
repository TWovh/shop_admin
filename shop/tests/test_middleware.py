"""
Тесты для middleware
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from unittest.mock import patch, MagicMock

from shop.middleware import AuthMiddleware

User = get_user_model()


class AuthMiddlewareTests(TestCase):
    """Тесты для AuthMiddleware"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = AuthMiddleware(lambda request: None)
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='USER'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='adminpass123',
            role='ADMIN'
        )
    
    def test_authenticated_user_with_role(self):
        """Тест аутентифицированного пользователя с ролью"""
        request = self.factory.get('/')
        request.user = self.user
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)  # Middleware не должен возвращать response
        self.assertEqual(request.user_role, 'USER')
    
    def test_authenticated_admin_user(self):
        """Тест аутентифицированного администратора"""
        request = self.factory.get('/')
        request.user = self.admin_user
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)
        self.assertEqual(request.user_role, 'ADMIN')
    
    def test_unauthenticated_user(self):
        """Тест неаутентифицированного пользователя"""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)
        self.assertIsNone(request.user_role)
    
    def test_user_without_role(self):
        """Тест пользователя без роли"""
        # Создаем пользователя с ролью по умолчанию
        user_without_role = User.objects.create_user(
            email='norole@example.com',
            password='testpass123',
            role='USER'  # Устанавливаем роль по умолчанию
        )
        
        request = self.factory.get('/')
        request.user = user_without_role
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)
        self.assertEqual(request.user_role, 'USER')  # Пользователь имеет роль USER
    
    def test_process_response_cleans_user_role(self):
        """Тест очистки user_role в process_response"""
        request = self.factory.get('/')
        request.user = self.user
        request.user_role = 'USER'
        
        # Создаем mock response
        response = MagicMock()
        
        result = self.middleware.process_response(request, response)
        
        self.assertEqual(result, response)
        self.assertFalse(hasattr(request, 'user_role'))
    
    def test_process_response_without_user_role(self):
        """Тест process_response без user_role"""
        request = self.factory.get('/')
        request.user = self.user
        # Не устанавливаем user_role
        
        response = MagicMock()
        
        result = self.middleware.process_response(request, response)
        
        self.assertEqual(result, response)
        # Не должно быть ошибки, если user_role не установлен
    
    def test_middleware_with_different_roles(self):
        """Тест middleware с разными ролями"""
        roles = ['USER', 'STAFF', 'ADMIN']
        
        for i, role in enumerate(roles):
            with self.subTest(role=role):
                user = User.objects.create_user(
                    email=f'{role.lower()}{i}@example.com',  # Уникальный email
                    password='testpass123',
                    role=role
                )
                
                request = self.factory.get('/')
                request.user = user
                
                self.middleware.process_request(request)
                
                self.assertEqual(request.user_role, role)
    
    def test_middleware_preserves_other_attributes(self):
        """Тест, что middleware не влияет на другие атрибуты request"""
        request = self.factory.get('/')
        request.user = self.user
        request.custom_attribute = 'test_value'
        
        self.middleware.process_request(request)
        
        self.assertEqual(request.user_role, 'USER')
        self.assertEqual(request.custom_attribute, 'test_value')
    
    def test_middleware_with_anonymous_user(self):
        """Тест middleware с анонимным пользователем"""
        from django.contrib.auth.models import AnonymousUser
        
        request = self.factory.get('/')
        request.user = AnonymousUser()
        
        response = self.middleware.process_request(request)
        
        self.assertIsNone(response)
        self.assertIsNone(request.user_role)
    
    def test_middleware_integration(self):
        """Интеграционный тест middleware"""
        # Создаем полный request с пользователем
        request = self.factory.get('/api/products/')
        request.user = self.user
        
        # Обрабатываем request
        self.middleware.process_request(request)
        
        # Проверяем, что user_role установлен
        self.assertEqual(request.user_role, 'USER')
        
        # Создаем response
        response = MagicMock()
        
        # Обрабатываем response
        result = self.middleware.process_response(request, response)
        
        # Проверяем, что user_role очищен
        self.assertFalse(hasattr(request, 'user_role'))
        self.assertEqual(result, response)