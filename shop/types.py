# улучшаем для понимания у джанго
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser, AbstractUser
from typing import Union
from .models import User

from django.http import HttpRequest
from django.contrib.auth.models import AbstractUser


class AuthenticatedRequest(HttpRequest):
    user: AbstractUser

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.GET = {}
        self.POST = {}
        self.COOKIES = {}
        self.FILES = {}
        self.META = {}

class AuthRequest(HttpRequest):
    """
    Общий тип для запросов, где user может быть как нашим User,
    так и AnonymousUser
    """
    user: Union[User, AnonymousUser]