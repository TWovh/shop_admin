from .types import AuthenticatedRequest
from django.http import HttpRequest

class AuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest):
        if request.user.is_authenticated:
            auth_request = AuthenticatedRequest()

            for attr in ['GET', 'POST', 'COOKIES', 'FILES', 'META', 'user']:
                if hasattr(request, attr):
                    setattr(auth_request, attr, getattr(request, attr))

            auth_request.META = request.META.copy()
            auth_request._body = getattr(request, '_body', None)

            request = auth_request

        return self.get_response(request)