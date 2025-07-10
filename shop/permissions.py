from rest_framework import permissions
from rest_framework.throttling import UserRateThrottle


class CustomPermission(permissions.BasePermission):

    def get_allowed_roles(self):
        return ['ADMIN', 'STAFF']

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if not hasattr(request.user, 'role'):
            return False

        return request.user_role in self.get_allowed_roles()

    def has_object_permission(self, request, view, obj):
        if request.user_role == 'ADMIN':
            return True

        if hasattr(obj, 'user'):
            return obj.user == request.user

        if hasattr(obj, 'cart') and getattr(obj.cart, 'user', None) == request.user:
            return True

        return False


class IsAdmin(CustomPermission):
    """Только для администраторов"""
    allowed_roles = ['ADMIN']


class IsStaff(CustomPermission):
    """Для персонала и администраторов"""
    allowed_roles = ['ADMIN', 'STAFF']

class IsUser(CustomPermission):
    allowed_roles = ['USER']

class IsAdminOrUser(CustomPermission):
    allowed_roles = ['ADMIN', 'USER']


class IsOwnerOrAdmin(CustomPermission):
    allowed_roles = ['ADMIN']

    def has_permission(self, request, view):
        # Разрешаем доступ только аутентифицированным
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Админ всегда может
        if request.user_role == 'ADMIN':
            return True

        # Проверка владельца объекта
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # Для других моделей с корзиной (если нужно)
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