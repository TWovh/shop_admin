# улучшаем для понимания у джанго
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser
from typing import Union
from .models import User

class AuthenticatedRequest(HttpRequest):
    """
    Кастомный тип для аутентифицированных запросов,
    где user точно является нашей моделью User
    """
    user: User

class AuthRequest(HttpRequest):
    """
    Общий тип для запросов, где user может быть как нашим User,
    так и AnonymousUser
    """
    user: Union[User, AnonymousUser]