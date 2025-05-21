from django.conf import settings
from django.conf.urls.static import static
from shop.admin_dashboard import admin_site
from shop.views import index
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from shop import views


router = DefaultRouter()
router.register(r'api/products', views.ProductViewSet)

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/', include(router.urls)),
    path('api/cart/', views.cart_detail, name='cart-detail'),# API для корзины
    path('api/cart/add/', views.add_to_cart, name='add-to-cart'),
    path('api/orders/', views.OrderListCreateView.as_view(), name='order-list'), #API заказов
    path('api/products/', include('shop.urls', namespace='products')),
    path('api/categories/', include('shop.urls', namespace='categories')),
    path('', index, name='index'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)