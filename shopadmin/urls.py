from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from shop.admin_dashboard import admin_site
from shop.views import index


urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/products/', include('shop.urls', namespace='products')),
    path('api/categories/', include('shop.urls', namespace='categories')),
    path('', index, name='index'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)