from rest_framework import permissions
from rest_framework.throttling import UserRateThrottle


class CustomPermission(permissions.BasePermission):

    allowed_roles = ['ADMIN', 'STAFF']  # Роли по умолчанию

    def has_permission(self, request, view):
        # Разрешаем только аутентифицированным пользователям
        if not request.user.is_authenticated:
            return False

        # Проверяем, что у пользователя есть атрибут role
        if not hasattr(request.user, 'role'):
            return False

        # Проверяем, что роль пользователя входит в разрешенные
        return request.user.role in self.allowed_roles

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'ADMIN':
            return True

        if hasattr(obj, 'user'):
            return obj.user == request.user

        if hasattr(obj, 'cart') and hasattr(obj.cart, 'user'):
            return obj.cart.user == request.user

        return False


class IsAdmin(CustomPermission):
    """Только для администраторов"""
    allowed_roles = ['ADMIN']


class IsStaff(CustomPermission):
    """Для персонала и администраторов"""
    allowed_roles = ['ADMIN', 'STAFF']


class IsOwnerOrAdmin(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        # Админам разрешаем всё
        if request.user.role == 'ADMIN':
            return True


        if hasattr(obj, 'user'):
            return obj.user == request.user

        return False



class CartThrottle(UserRateThrottle):
    """
    Ограничение частоты запросов для корзины
    """
    scope = 'cart'  # Уникальный идентификатор для настроек
    rate = '10/minute'  # 10 запросов в минуту
    def get_rate(self):
        if self.request.user.role == 'ADMIN':
            return '100/minute'  # Админам больше запросов
        return '10/minute'  # Обычным пользователям меньше