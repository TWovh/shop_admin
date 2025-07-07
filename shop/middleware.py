from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest
from .types import AuthenticatedRequest, User



class AuthMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        if request.user.is_authenticated:
            request.authenticated_user = request.user
            request.user_role = request.user.role  # Теперь user точно имеет role
        # Для анонимных пользователей
        else:
            request.authenticated_user = None
            request.user_role = None  # Или установите значение по умолчанию

        return None

    def process_response(self, request: HttpRequest, response):
        if hasattr(request, 'authenticated_user'):
            del request.authenticated_user
        if hasattr(request, 'user_role'):
            del request.user_role
        return response