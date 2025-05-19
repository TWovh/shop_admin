from django.contrib import admin
from django.db.models import Count, Sum, F
from django.urls import path
from django.shortcuts import render
from .models import Product, Order, Category


class AdminDashboard(admin.AdminSite):
    index_template = 'admin/dashboard.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('statistics/', self.admin_view(self.statistics_view),
        ]
        return custom_urls + urls

    def statistics_view(self, request):
        # Статистика по продажам
        sales_data = (
            Order.objects
            .values('created__date')
            .annotate(total=Sum('total_price'))

            # Топ товаров
            top_products = (
            Product.objects
            .annotate(order_count=Count('order_items'))
        .order_by('-order_count')[:5])

        context = {
            'sales_data': list(sales_data),
            'top_products': top_products,
            'opts': self._build_app_dict(request)['shop'],
        }
        return render(request, 'admin/statistics.html', context)


# Заменяем стандартную админку
admin_site = AdminDashboard(name='myadmin')


# Регистрируем модели с кастомизацией для дашборда
@admin.register(Product, site=admin_site)
class ProductAdmin(admin.ModelAdmin):


# ... существующий код ...

@admin.register(Order, site=admin_site)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_price', 'status', 'created')
    list_filter = ('status', 'created')


def index(self, request, extra_context=None):
    extra_context = extra_context or {}

    # Основная статистика
    extra_context.update({
        'total_sales': Order.objects.aggregate(Sum('total_price'))['total_price__sum'] or 0,
        'product_count': Product.objects.count(),
        'sales_labels': [str(item['created__date']) for item in sales_data],
        'sales_values': [float(item['total']) for item in sales_data],
        'product_names': [p.name for p in top_products],
        'product_sales': [p.order_count for p in top_products]
    })

    return super().index(request, extra_context)