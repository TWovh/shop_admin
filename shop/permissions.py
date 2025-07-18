from rest_framework import permissions
from rest_framework.throttling import UserRateThrottle


class CustomPermission(permissions.BasePermission):
    allowed_roles = ['ADMIN', 'STAFF']  # Значение по умолчанию

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(request.user, 'role', None)
        if role is None:
            return False

        return role in self.allowed_roles

    def has_object_permission(self, request, view, obj):
        role = getattr(request.user, 'role', None)

        if role == 'ADMIN':
            return True  # Админ всегда может

        # Если объект имеет поле user — проверяем владение
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # Если объект связан с корзиной, проверяем пользователя корзины
        if hasattr(obj, 'cart') and getattr(obj.cart, 'user', None) == request.user:
            return True

        return False


class IsAdmin(CustomPermission):
    allowed_roles = ['ADMIN']


class IsStaff(CustomPermission):
    allowed_roles = ['ADMIN', 'STAFF']


class IsUser(CustomPermission):
    allowed_roles = ['USER']

class IsAdminOrUser(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        role = getattr(request.user, 'role', None)
        return role in ['ADMIN', 'USER']


class IsOwnerOrAdmin(CustomPermission):
    allowed_roles = ['ADMIN']

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if getattr(request.user, 'role', None) == 'ADMIN':
            return True

        if hasattr(obj, 'user'):
            return obj.user == request.user

        if hasattr(obj, 'cart') and hasattr(obj.cart, 'user'):
            return obj.cart.user == request.user

        return False



class CartThrottle(UserRateThrottle):
    """
    Ограничение частоты запросов для корзины
    """
    scope = 'cart'  # Уникальный идентификатор для настроек
    rate = '10/minute'  # 10 запросов в минуту
    def get_rate(self):
        if self.request.user_role == 'ADMIN':
            return '100/minute'  # Админам больше запросов
        return '10/minute'  # Обычным пользователям меньше