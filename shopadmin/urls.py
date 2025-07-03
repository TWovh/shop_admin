from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from shop.admin_dashboard import admin_site
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from shop.views import index, register


urlpatterns = [
    path('', include(('shop.urls_views', 'shop'), namespace='shop')),  # старый frontend (Django templates)
    path('admin/', admin_site.urls),
    path('api/', include('shop.urls_api')),
    # JWT Authentication
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('register/', register, name='register'),

    # Auth views
    path('auth/', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)