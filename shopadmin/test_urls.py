"""
URL'ы для тестирования
"""
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()

# Простые view для тестирования
def user_me(request):
    if request.user.is_authenticated:
        return JsonResponse({
            'id': request.user.id,
            'email': request.user.email,
            'role': request.user.role
        })
    return JsonResponse({'detail': 'Not authenticated'}, status=401)

api_urlpatterns = [
    # JWT аутентификация (заглушки)
    path('auth/token/', user_me, name='token_obtain_pair'),
    path('auth/token/refresh/', user_me, name='token_refresh'),
    path('auth/me/', user_me, name='user_me'),
    
    # Webhooks (заглушки для тестов)
    path('webhooks/stripe/', lambda request: HttpResponse('OK'), name='stripe-webhook'),
    path('webhooks/paypal/', lambda request: HttpResponse('OK'), name='paypal-webhook'),
    path('webhooks/fondy/', lambda request: HttpResponse('OK'), name='fondy-webhook'),
    path('webhooks/liqpay/', lambda request: HttpResponse('OK'), name='liqpay-webhook'),
    path('webhooks/portmone/', lambda request: HttpResponse('OK'), name='portmone-webhook'),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(api_urlpatterns)),
]