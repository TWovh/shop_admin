"""
Тесты для кастомных разрешений
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from unittest.mock import MagicMock

from shop.permissions import (
    CustomPermission, IsAdmin, IsStaff, IsUser, 
    IsAdminOrUser, IsOwnerOrAdmin, CartThrottle
)
from shop.models import Order, Product, Category, Cart, CartItem

User = get_user_model()


class CustomPermissionTests(TestCase):
    """Тесты для базового класса CustomPermission"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            role='USER'
        )
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='testpass123',
            role='STAFF'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role='ADMIN'
        )
        self.anonymous_user = None
    
    def test_custom_permission_abstract(self):
        """Тест, что CustomPermission является абстрактным классом"""
        permission = CustomPermission()
        permission.allowed_roles = ['USER']
        
        # Тест с аутентифицированным пользователем
        request = self.factory.get('/')
        request.user = self.user
        
        result = permission.has_permission(request, None)
        self.assertTrue(result)
    
    def test_custom_permission_unauthenticated(self):
        """Тест CustomPermission с неаутентифицированным пользователем"""
        permission = CustomPermission()
        permission.allowed_roles = ['USER']
        
        request = self.factory.get('/')
        request.user = None
        
        result = permission.has_permission(request, None)
        self.assertFalse(result)
    
    def test_custom_permission_user_without_role(self):
        """Тест CustomPermission с пользователем без роли"""
        user_without_role = User.objects.create_user(
            email='norole@example.com',
            password='testpass123',
            role='USER'  # Устанавливаем роль по умолчанию
        )
        
        permission = CustomPermission()
        permission.allowed_roles = ['USER']
        
        request = self.factory.get('/')
        request.user = user_without_role
        
        result = permission.has_permission(request, None)
        self.assertFalse(result)


class IsAdminTests(TestCase):
    """Тесты для IsAdmin разрешения"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            role='USER'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role='ADMIN'
        )
        self.permission = IsAdmin()
    
    def test_admin_has_permission(self):
        """Тест, что администратор имеет разрешение"""
        request = self.factory.get('/')
        request.user = self.admin_user
        
        result = self.permission.has_permission(request, None)
        self.assertTrue(result)
    
    def test_user_has_no_permission(self):
        """Тест, что обычный пользователь не имеет разрешения"""
        request = self.factory.get('/')
        request.user = self.user
        
        result = self.permission.has_permission(request, None)
        self.assertFalse(result)
    
    def test_unauthenticated_has_no_permission(self):
        """Тест, что неаутентифицированный пользователь не имеет разрешения"""
        request = self.factory.get('/')
        request.user = None
        
        result = self.permission.has_permission(request, None)
        self.assertFalse(result)


class IsStaffTests(TestCase):
    """Тесты для IsStaff разрешения"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            role='USER'
        )
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='testpass123',
            role='STAFF'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role='ADMIN'
        )
        self.permission = IsStaff()
    
    def test_admin_has_permission(self):
        """Тест, что администратор имеет разрешение"""
        request = self.factory.get('/')
        request.user = self.admin_user
        
        result = self.permission.has_permission(request, None)
        self.assertTrue(result)
    
    def test_staff_has_permission(self):
        """Тест, что персонал имеет разрешение"""
        request = self.factory.get('/')
        request.user = self.staff_user
        
        result = self.permission.has_permission(request, None)
        self.assertTrue(result)
    
    def test_user_has_no_permission(self):
        """Тест, что обычный пользователь не имеет разрешения"""
        request = self.factory.get('/')
        request.user = self.user
        
        result = self.permission.has_permission(request, None)
        self.assertFalse(result)


class IsUserTests(TestCase):
    """Тесты для IsUser разрешения"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            role='USER'
        )
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='testpass123',
            role='STAFF'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role='ADMIN'
        )
        self.permission = IsUser()
    
    def test_all_authenticated_users_have_permission(self):
        """Тест, что все аутентифицированные пользователи имеют разрешение"""
        users = [self.user, self.staff_user, self.admin_user]
        
        for user in users:
            with self.subTest(user=user.email):
                request = self.factory.get('/')
                request.user = user
                
                result = self.permission.has_permission(request, None)
                self.assertTrue(result)
    
    def test_unauthenticated_has_no_permission(self):
        """Тест, что неаутентифицированный пользователь не имеет разрешения"""
        request = self.factory.get('/')
        request.user = None
        
        result = self.permission.has_permission(request, None)
        self.assertFalse(result)


class IsAdminOrUserTests(TestCase):
    """Тесты для IsAdminOrUser разрешения"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            role='USER'
        )
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='testpass123',
            role='STAFF'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role='ADMIN'
        )
        self.permission = IsAdminOrUser()
    
    def test_admin_has_permission(self):
        """Тест, что администратор имеет разрешение"""
        request = self.factory.get('/')
        request.user = self.admin_user
        
        result = self.permission.has_permission(request, None)
        self.assertTrue(result)
    
    def test_user_has_permission(self):
        """Тест, что обычный пользователь имеет разрешение"""
        request = self.factory.get('/')
        request.user = self.user
        
        result = self.permission.has_permission(request, None)
        self.assertTrue(result)
    
    def test_staff_has_no_permission(self):
        """Тест, что персонал не имеет разрешения"""
        request = self.factory.get('/')
        request.user = self.staff_user
        
        result = self.permission.has_permission(request, None)
        self.assertFalse(result)


class IsOwnerOrAdminTests(TestCase):
    """Тесты для IsOwnerOrAdmin разрешения"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            role='USER'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            role='USER'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role='ADMIN'
        )
        self.permission = IsOwnerOrAdmin()
        
        # Создаем объект с пользователем
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
        
        self.order = Order.objects.create(
            user=self.user,
            address='Тестовый адрес',
            phone='+380501234567',
            email='user@example.com',
            city='Киев'
        )
    
    def test_admin_has_permission_for_any_object(self):
        """Тест, что администратор имеет разрешение для любого объекта"""
        request = self.factory.get('/')
        request.user = self.admin_user
        
        result = self.permission.has_object_permission(request, None, self.order)
        self.assertTrue(result)
    
    def test_owner_has_permission_for_own_object(self):
        """Тест, что владелец имеет разрешение для своего объекта"""
        request = self.factory.get('/')
        request.user = self.user
        
        result = self.permission.has_object_permission(request, None, self.order)
        self.assertTrue(result)
    
    def test_other_user_has_no_permission(self):
        """Тест, что другой пользователь не имеет разрешения"""
        request = self.factory.get('/')
        request.user = self.other_user
        
        result = self.permission.has_object_permission(request, None, self.order)
        self.assertFalse(result)
    
    def test_object_without_user_field(self):
        """Тест объекта без поля user"""
        request = self.factory.get('/')
        request.user = self.user
        
        result = self.permission.has_object_permission(request, None, self.product)
        self.assertFalse(result)
    
    def test_object_with_cart_field(self):
        """Тест объекта с полем cart"""
        cart = Cart.objects.create(user=self.user)
        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        result = self.permission.has_object_permission(request, None, cart_item)
        self.assertTrue(result)
    
    def test_object_with_cart_field_other_user(self):
        """Тест объекта с полем cart другого пользователя"""
        other_cart = Cart.objects.create(user=self.other_user)
        cart_item = CartItem.objects.create(
            cart=other_cart,
            product=self.product,
            quantity=1
        )
        
        request = self.factory.get('/')
        request.user = self.user
        
        result = self.permission.has_object_permission(request, None, cart_item)
        self.assertFalse(result)


class CartThrottleTests(TestCase):
    """Тесты для CartThrottle"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            email='user@example.com',
            password='testpass123',
            role='USER'
        )
        self.staff_user = User.objects.create_user(
            email='staff@example.com',
            password='testpass123',
            role='STAFF'
        )
        self.admin_user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123',
            role='ADMIN'
        )
        self.throttle = CartThrottle()
    
    def test_throttle_scope(self):
        """Тест области действия throttle"""
        # Создаем throttle с request
        request = self.factory.get('/')
        request.user = self.user
        throttle = CartThrottle()
        throttle.request = request
        self.assertEqual(throttle.scope, 'cart')
    
    def test_admin_rate_limit(self):
        """Тест лимита для администратора"""
        request = self.factory.get('/')
        request.user = self.admin_user
        self.throttle.request = request
        
        rate = self.throttle.get_rate()
        self.assertEqual(rate, '100/minute')
    
    def test_staff_rate_limit(self):
        """Тест лимита для персонала"""
        request = self.factory.get('/')
        request.user = self.staff_user
        self.throttle.request = request
        
        rate = self.throttle.get_rate()
        self.assertEqual(rate, '50/minute')
    
    def test_user_rate_limit(self):
        """Тест лимита для обычного пользователя"""
        request = self.factory.get('/')
        request.user = self.user
        self.throttle.request = request
        
        rate = self.throttle.get_rate()
        self.assertEqual(rate, '10/minute')
    
    def test_unauthenticated_rate_limit(self):
        """Тест лимита для неаутентифицированного пользователя"""
        request = self.factory.get('/')
        request.user = None
        self.throttle.request = request
        
        rate = self.throttle.get_rate()
        self.assertEqual(rate, '10/minute')  # По умолчанию
    
    def test_user_without_role_rate_limit(self):
        """Тест лимита для пользователя без роли"""
        user_without_role = User.objects.create_user(
            email='norole@example.com',
            password='testpass123'
        )
        user_without_role.role = None
        user_without_role.save()
        
        request = self.factory.get('/')
        request.user = user_without_role
        self.throttle.request = request
        
        rate = self.throttle.get_rate()
        self.assertEqual(rate, '10/minute')  # По умолчанию