from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from shop.admin_dashboard import admin_site

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/', include('shop.urls_api')),
    path('', include('shop.urls_views')),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)