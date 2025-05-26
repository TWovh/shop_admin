from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser, AbstractUser
from typing import Union
from .models import User


class AuthenticatedRequest(HttpRequest):
    authenticated_user: User  # Лучше использовать вашу конкретную модель User
    user_role: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # Это инициализирует GET, POST, FILES и т.д. правильно!

        # Теперь просто добавляем или инициализируем наши кастомные поля
        self.authenticated_user = getattr(self, 'user', None) if getattr(self, 'user', None) and getattr(self,
                                                                                                         'user').is_authenticated else None  # type: ignore
        self.user_role = getattr(getattr(self, 'user', None), 'role', '') if self.authenticated_user else ''



    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, value):
        self._body = value

class AuthRequest(HttpRequest):
    """
    Общий тип для запросов, где user может быть как нашим User,
    так и AnonymousUser
    """
    user: Union[User, AnonymousUser]