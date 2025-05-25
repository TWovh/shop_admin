from .types import AuthenticatedRequest
from django.http import HttpRequest

class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        # Приводим тип после аутентификации
        if hasattr(request, 'user') and request.user.is_authenticated:
            request.__class__ = AuthenticatedRequest
        return self.get_response(request)