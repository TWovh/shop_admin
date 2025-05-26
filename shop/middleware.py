from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest
# Импорт AuthenticatedRequest и User из types.py для аннотаций типов, если нужно


# Если вы хотите использовать ваш AuthenticatedRequest для тайп-хинтинга в представлениях,
# вы можете его импортировать, но не использовать для изменения __class__
# from .types import AuthenticatedRequest as AuthenticatedRequestTypeHint

class AuthMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        if request.user.is_authenticated:


            # Для type checker'ов можно сделать так, чтобы они знали о новых атрибутах:
            setattr(request, 'authenticated_user', request.user)
            setattr(request, 'user_role', getattr(request.user, 'role', None))  # Безопасное получение роли


        request.authenticated_user = request.user
        request.user_role = request.user.role

        return None

    def process_response(self, request: HttpRequest, response):
        if hasattr(request, 'authenticated_user'):
            delattr(request, 'authenticated_user')
        if hasattr(request, 'user_role'):
            delattr(request, 'user_role')
        return response