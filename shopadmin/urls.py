from django.contrib import admin
from django.urls import path, include
from shop.views import home
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/products/', include('shop.urls', namespace='products')),
    path('api/categories/', include('shop.urls', namespace='categories')),
    path('', home, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)