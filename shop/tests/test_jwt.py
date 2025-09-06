"""
Тесты для JWT аутентификации
"""
import json
import base64
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from unittest.mock import patch
from shop.serializers import CustomTokenObtainPairSerializer

User = get_user_model()


class JWTTestCase(TestCase):
    """Базовый класс для JWT тестов"""
    
    def setUp(self):
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
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='staffpass123',
            role='STAFF'
        )
        self.client = Client()


class JWTTokenGenerationTests(JWTTestCase):
    """Тесты генерации JWT токенов"""
    
    def test_token_generation_for_user(self):
        """Тест генерации токена для обычного пользователя"""
        serializer = CustomTokenObtainPairSerializer()
        refresh = serializer.get_token(self.user)
        access_token = refresh.access_token
        
        # Проверяем структуру токена
        self.assertIsNotNone(str(access_token))
        self.assertIsNotNone(str(refresh))
        
        # Декодируем payload
        payload = self._decode_jwt_payload(access_token)
        
        # Проверяем содержимое payload
        self.assertEqual(payload['user_id'], self.user.id)
        self.assertEqual(payload['email'], self.user.email)
        self.assertEqual(payload['role'], 'USER')
        self.assertEqual(payload['permissions'], ['user_access'])
        self.assertFalse(payload['is_staff'])
        self.assertFalse(payload['is_superuser'])
    
    def test_token_generation_for_admin(self):
        """Тест генерации токена для администратора"""
        serializer = CustomTokenObtainPairSerializer()
        refresh = serializer.get_token(self.admin_user)
        access_token = refresh.access_token
        
        payload = self._decode_jwt_payload(access_token)
        
        self.assertEqual(payload['user_id'], self.admin_user.id)
        self.assertEqual(payload['email'], self.admin_user.email)
        self.assertEqual(payload['role'], 'ADMIN')
        self.assertEqual(payload['permissions'], ['full_access'])
        self.assertTrue(payload['is_staff'])
        self.assertTrue(payload['is_superuser'])
    
    def test_token_generation_for_staff(self):
        """Тест генерации токена для персонала"""
        serializer = CustomTokenObtainPairSerializer()
        refresh = serializer.get_token(self.staff_user)
        access_token = refresh.access_token
        
        payload = self._decode_jwt_payload(access_token)
        
        self.assertEqual(payload['user_id'], self.staff_user.id)
        self.assertEqual(payload['email'], self.staff_user.email)
        self.assertEqual(payload['role'], 'STAFF')
        self.assertEqual(payload['permissions'], ['staff_access'])
        self.assertTrue(payload['is_staff'])
        self.assertFalse(payload['is_superuser'])
    
    def test_token_lifetime(self):
        """Тест времени жизни токенов"""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        payload = self._decode_jwt_payload(access_token)
        
        # Проверяем, что токен создан недавно
        import time
        current_time = int(time.time())
        token_iat = payload['iat']
        token_exp = payload['exp']
        
        # Токен должен быть создан в последние 5 секунд
        self.assertLessEqual(current_time - token_iat, 5)
        
        # Access токен должен истекать через 15 минут
        expected_exp = token_iat + (15 * 60)  # 15 минут
        self.assertEqual(token_exp, expected_exp)
    
    def _decode_jwt_payload(self, token):
        """Декодирует payload JWT токена"""
        try:
            parts = str(token).split('.')
            if len(parts) != 3:
                return None
            
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return None


class JWTAuthenticationAPITests(APITestCase):
    """Тесты JWT аутентификации через API"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            role='USER'
        )
        self.login_url = reverse('token_obtain_pair')
        self.refresh_url = reverse('token_refresh')
        self.user_me_url = reverse('user_me')
    
    def test_login_with_valid_credentials(self):
        """Тест входа с валидными учетными данными"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        
        # Проверяем данные пользователя в ответе
        user_data = response.data['user']
        self.assertEqual(user_data['email'], 'test@example.com')
        self.assertEqual(user_data['role'], 'USER')
        self.assertEqual(user_data['id'], self.user.id)
    
    def test_login_with_invalid_credentials(self):
        """Тест входа с невалидными учетными данными"""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }
        
        response = self.client.post(self.login_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        # Для заглушки проверяем JSON ответ
        import json
        response_data = json.loads(response.content)
        self.assertIn('detail', response_data)
    
    def test_token_refresh(self):
        """Тест обновления токена"""
        # Сначала получаем токены
        refresh = RefreshToken.for_user(self.user)
        
        data = {
            'refresh': str(refresh)
        }
        
        response = self.client.post(self.refresh_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        
        # Новый access токен должен отличаться от старого
        new_access = response.data['access']
        self.assertNotEqual(str(refresh.access_token), new_access)
    
    def test_token_refresh_with_invalid_token(self):
        """Тест обновления токена с невалидным refresh токеном"""
        data = {
            'refresh': 'invalid_token'
        }
        
        response = self.client.post(self.refresh_url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_authenticated_request(self):
        """Тест аутентифицированного запроса"""
        # Получаем токен
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        
        # Делаем запрос с токеном
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(self.user_me_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
    
    def test_unauthenticated_request(self):
        """Тест неаутентифицированного запроса"""
        response = self.client.get(self.user_me_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_expired_token(self):
        """Тест истекшего токена"""
        # Создаем токен с истекшим временем
        with patch('rest_framework_simplejwt.tokens.timezone') as mock_timezone:
            # Устанавливаем время в прошлом
            from datetime import datetime, timedelta
            past_time = datetime.now() - timedelta(hours=1)
            mock_timezone.now.return_value = past_time
            
            refresh = RefreshToken.for_user(self.user)
            access_token = str(refresh.access_token)
        
        # Делаем запрос с истекшим токеном
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(self.user_me_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class JWTSecurityTests(JWTTestCase):
    """Тесты безопасности JWT"""
    
    def test_token_rotation(self):
        """Тест ротации refresh токенов"""
        refresh = RefreshToken.for_user(self.user)
        old_refresh = str(refresh)
        
        # Обновляем токен
        new_refresh = refresh.access_token
        
        # Старый refresh токен должен быть в blacklist
        with self.assertRaises(TokenError):
            RefreshToken(old_refresh)
    
    def test_token_blacklist(self):
        """Тест blacklist токенов"""
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        
        # Добавляем токен в blacklist
        refresh.blacklist()
        
        # Токен должен быть недействителен
        with self.assertRaises(TokenError):
            RefreshToken(access_token)
    
    def test_token_tampering(self):
        """Тест подделки токена"""
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        
        # Подделываем токен
        tampered_token = access_token[:-5] + 'XXXXX'
        
        # Подделанный токен должен быть недействителен
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {tampered_token}')
        response = self.client.get(reverse('user_me'))
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_token_structure(self):
        """Тест структуры JWT токена"""
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        
        # JWT должен состоять из 3 частей
        parts = access_token.split('.')
        self.assertEqual(len(parts), 3)
        
        # Проверяем, что части не пустые
        for part in parts:
            self.assertNotEqual(part, '')
    
    def test_token_payload_integrity(self):
        """Тест целостности payload токена"""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        payload = self._decode_jwt_payload(access_token)
        
        # Проверяем обязательные поля
        required_fields = ['user_id', 'email', 'role', 'permissions', 'exp', 'iat', 'jti']
        for field in required_fields:
            self.assertIn(field, payload)
        
        # Проверяем типы данных
        self.assertIsInstance(payload['user_id'], int)
        self.assertIsInstance(payload['email'], str)
        self.assertIsInstance(payload['role'], str)
        self.assertIsInstance(payload['permissions'], list)
        self.assertIsInstance(payload['exp'], int)
        self.assertIsInstance(payload['iat'], int)
        self.assertIsInstance(payload['jti'], str)
    
    def _decode_jwt_payload(self, token):
        """Декодирует payload JWT токена"""
        try:
            parts = str(token).split('.')
            if len(parts) != 3:
                return None
            
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return None


class JWTPermissionsTests(JWTTestCase):
    """Тесты разрешений в JWT токенах"""
    
    def test_user_permissions(self):
        """Тест разрешений обычного пользователя"""
        refresh = RefreshToken.for_user(self.user)
        access_token = refresh.access_token
        
        payload = self._decode_jwt_payload(access_token)
        
        self.assertEqual(payload['permissions'], ['user_access'])
        self.assertNotIn('staff_access', payload['permissions'])
        self.assertNotIn('full_access', payload['permissions'])
    
    def test_staff_permissions(self):
        """Тест разрешений персонала"""
        refresh = RefreshToken.for_user(self.staff_user)
        access_token = refresh.access_token
        
        payload = self._decode_jwt_payload(access_token)
        
        self.assertEqual(payload['permissions'], ['staff_access'])
        self.assertNotIn('full_access', payload['permissions'])
    
    def test_admin_permissions(self):
        """Тест разрешений администратора"""
        refresh = RefreshToken.for_user(self.admin_user)
        access_token = refresh.access_token
        
        payload = self._decode_jwt_payload(access_token)
        
        self.assertEqual(payload['permissions'], ['full_access'])
    
    def _decode_jwt_payload(self, token):
        """Декодирует payload JWT токена"""
        try:
            parts = str(token).split('.')
            if len(parts) != 3:
                return None
            
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception:
            return None


class JWTIntegrationTests(APITestCase):
    """Интеграционные тесты JWT"""
    
    def setUp(self):
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
    
    def test_full_authentication_flow(self):
        """Тест полного цикла аутентификации"""
        # 1. Логин
        login_data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }
        
        login_response = self.client.post(reverse('token_obtain_pair'), login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']
        
        # 2. Аутентифицированный запрос
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        user_response = self.client.get(reverse('user_me'))
        self.assertEqual(user_response.status_code, status.HTTP_200_OK)
        
        # 3. Обновление токена
        refresh_data = {'refresh': refresh_token}
        refresh_response = self.client.post(reverse('token_refresh'), refresh_data, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        
        new_access_token = refresh_response.data['access']
        
        # 4. Запрос с новым токеном
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access_token}')
        user_response = self.client.get(reverse('user_me'))
        self.assertEqual(user_response.status_code, status.HTTP_200_OK)
    
    def test_token_expiration_handling(self):
        """Тест обработки истечения токена"""
        # Создаем токен
        refresh = RefreshToken.for_user(self.user)
        access_token = str(refresh.access_token)
        
        # Делаем запрос с токеном
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(reverse('user_me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Имитируем истечение токена (в реальности это произойдет через 15 минут)
        # Здесь мы просто проверяем, что система корректно обрабатывает невалидные токены
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid_token')
        response = self.client.get(reverse('user_me'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_multiple_user_sessions(self):
        """Тест множественных сессий пользователей"""
        # Создаем токены для разных пользователей
        user_refresh = RefreshToken.for_user(self.user)
        admin_refresh = RefreshToken.for_user(self.admin_user)
        
        user_token = str(user_refresh.access_token)
        admin_token = str(admin_refresh.access_token)
        
        # Проверяем, что токены разные
        self.assertNotEqual(user_token, admin_token)
        
        # Проверяем доступ с разными токенами
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {user_token}')
        user_response = self.client.get(reverse('user_me'))
        self.assertEqual(user_response.data['email'], 'test@example.com')
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        admin_response = self.client.get(reverse('user_me'))
        self.assertEqual(admin_response.data['email'], 'admin@example.com')