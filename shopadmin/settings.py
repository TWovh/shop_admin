from pathlib import Path
import os
from datetime import timedelta

from corsheaders.defaults import default_headers
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

# Безопасность
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY не найден в переменных окружения!")

DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'  

# URLs
FRONTEND_URL = os.getenv('FRONTEND_URL', "http://localhost:5173")
BACKEND_URL = os.getenv('BACKEND_URL', "http://127.0.0.1:8000")
SITE_URL = os.getenv('SITE_URL', "http://127.0.0.1:8000")

# CORS настройки
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    FRONTEND_URL,
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    FRONTEND_URL,
]

# Безопасность хостов (для разработки)
ALLOWED_HOSTS = ['*'] if DEBUG else os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Модель пользователя
AUTH_USER_MODEL = 'shop.User'

# Безопасность
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# SSL редирект (в продакшене True)
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'

X_FRAME_OPTIONS = 'DENY'

# Безопасность куки (для разработки)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Куки нельзя прочитать из JS
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # CSRF токен читается React-ом (JS)

# Не передаются с других сайтов
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Разрешаем браузеру слать куки
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = list(default_headers) + [
    "ngrok-skip-browser-warning",
]

# Авторизация
LOGIN_URL = '/admin/login/'
LOGIN_REDIRECT_URL = '/admin/'
LOGOUT_REDIRECT_URL = '/admin/login/'

# Хеширование паролей
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
]

# Логирование
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
            'formatter': 'verbose',
            'level': 'INFO',
        },
        'payment_file': {
            'class': 'logging.FileHandler',
            'filename': 'payment.log',
            'formatter': 'verbose',
            'level': 'INFO',
        },
    },
    'loggers': {
        'shop.views_payments': {
            'handlers': ['console', 'payment_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'shop.utils': {
            'handlers': ['console', 'payment_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'shop.clients': {
            'handlers': ['console', 'payment_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "rest_framework.authtoken",
    "shop.apps.ShopConfig",
    "django.contrib.humanize",
    "corsheaders",
    "dal",
    "dal_select2",

]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "shop.middleware.AuthMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "shopadmin.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, 'templates')]
        ,
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "shopadmin.wsgi.application"


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'shop',
        'USER': 'postgres',
        'PASSWORD': 'death1965',
        'HOST': 'db' if os.getenv('DOCKER') == 'yes' else 'localhost',
        'PORT': '5432',
    }
}

EMAIL_BACKEND = os.getenv('EMAIL_BACKEND')
EMAIL_HOST = os.getenv('EMAIL_HOST')
EMAIL_PORT = int(os.getenv('EMAIL_PORT'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS') == 'True'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL')

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_RENDERER_CLASSES': [
            'rest_framework.renderers.JSONRenderer',
            'rest_framework.renderers.TemplateHTMLRenderer',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '100/hour',  # Лимит по умолчанию
        'cart': '10/minute',  # Лимит для корзины
        'payment': '10/minute',  # Лимит для платежей
        'webhook': '100/minute',  # Лимит для вебхуков
    }
}

SIMPLE_JWT = {
    # Время жизни токенов
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    
    # Безопасность
    'ROTATE_REFRESH_TOKENS': True,                    
    'BLACKLIST_AFTER_ROTATION': True,                 
    
    # Настройки для React (без HttpOnly cookies)
    # Токены будут передаваться в заголовках Authorization
    
    # Заголовки (для обратной совместимости)
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_OBTAIN_SERIALIZER': 'shop.serializers.CustomTokenObtainPairSerializer',
    
    # Дополнительная безопасность
    'SLIDING_TOKEN_REFRESH_EXP_CLAIM': 'refresh_exp',
    'SLIDING_TOKEN_LIFETIME': timedelta(minutes=5),
    'SLIDING_TOKEN_REFRESH_LIFETIME': timedelta(days=1),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')




LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Директория для collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')



SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Redis настройки
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# Celery настройки
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Kiev'
CELERY_ENABLE_UTC = True

# Настройки для retry механизма
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_RETRY_POLICY = {
    'max_retries': 3,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 0.2,
}

# Кэширование с Redis (временно отключено для тестирования)
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}',
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         }
#     }
# }

# Временный кэш для тестирования (без Redis)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}
