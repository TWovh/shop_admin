from django.conf import settings
from django.conf.urls.static import static
from shop.admin_dashboard import admin_site
from shop.views import index
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from shop import views


router = DefaultRouter()
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'categories', views.CategoryViewSet, basename='category')

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/', include([
        path('', include(router.urls)),
        path('cart/', views.cart_detail, name='cart-detail'),
        path('cart/add/', views.add_to_cart, name='add-to-cart'),
        path('orders/', views.OrderListCreateView.as_view(), name='order-list'),
    ])),
    path('', index, name='index'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
