from typing import Union
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser
from shop.models import User


class AuthenticatedRequest(HttpRequest):
    user: User  # уже аутентифицированный
    user_role: str


class AuthRequest(HttpRequest):
    user: Union[User, AnonymousUser]