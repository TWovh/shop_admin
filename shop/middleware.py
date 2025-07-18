from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest

class AuthMiddleware(MiddlewareMixin):
    def process_request(self, request: HttpRequest):
        if request.user.is_authenticated:
            request.user_role = getattr(request.user, 'role', None)
        else:
            request.user_role = None
        return None

    def process_response(self, request: HttpRequest, response):
        if hasattr(request, 'user_role'):
            del request.user_role
        return response