from rest_framework import permissions


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
        # Дополнительная проверка на уровне объекта
        return self.has_permission(request, view)


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