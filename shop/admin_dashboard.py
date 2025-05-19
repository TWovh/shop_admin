from .models import Product, Order, Category
from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.http import Http404



class AdminDashboard(admin.AdminSite):
    index_template = 'admin/dashboard.html'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('statistics/', self.admin_view(self.statistics_view)),
        ]
        return custom_urls + urls

    def get_dashboard_stats(self):          # Статистика продаж за последние 30 дней

        sales_data = (
            Order.objects
            .filter(created__gte=timezone.now() - timedelta(days=30))
            .values('created__date')
            .annotate(total=Sum('total_price'))
            .order_by('created__date')
        )

        top_products = (
            Product.objects
            .annotate(
                total_ordered=Count('order_items'),
                total_revenue=Sum('order_items__price')
            )
            .order_by('-total_ordered')[:5]
        )

        total_stats = Order.objects.aggregate(
            total_sales=Sum('total_price'),
            avg_order=Avg('total_price')
        )

        return {
            'sales_data': list(sales_data),
            'sales_labels': [item['created__date'].strftime('%Y-%m-%d') for item in sales_data],
            'sales_values': [float(item['total']) for item in sales_data],
            'top_products': top_products,
            'total_sales': total_stats['total_sales'] or 0,
            'avg_order': total_stats['avg_order'] or 0,
            'product_count': Product.objects.count()
        }

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        stats = self.get_dashboard_stats()

        extra_context.update({
            'total_sales': stats['total_sales'],
            'product_count': stats['product_count'],
            'sales_labels': [str(item['created__date']) for item in stats['sales_data']],
            'sales_values': [float(item['total']) for item in stats['sales_data']],
            'product_names': [p.name for p in stats['top_products']],
            'product_sales': [p.total_ordered for p in stats['top_products']]
        })

        return super().index(request, extra_context)

    def statistics_view(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        orders = Order.objects.all()

        if start_date:
            orders = orders.filter(created__gte=start_date)
        if end_date:
            orders = orders.filter(created__lte=end_date)

        paginator = Paginator(orders, 25)
        page_number = request.GET.get('page')

        try:
            page_obj = paginator.get_page(page_number)
        except Http404:
            page_obj = paginator.get_page(1)

        categories_stats = (
            Category.objects
            .annotate(total_sales=Sum('products__order_items__price'))
            .exclude(total_sales=None)
            .order_by('-total_sales')
        )

        context = {
            'total_sales': orders.aggregate(total=Sum('total_price'))['total'] or 0,
            'orders_count': orders.count(),
            'recent_orders': orders.order_by('-created')[:10],
            'categories_labels': [cat.name for cat in categories_stats],
            'categories_values': [float(cat.total_sales) for cat in categories_stats],
            **self.each_context(request),
            'title': 'Статистика продаж',
        }
        return render(request, 'admin/statistics.html', context)

# Замена админки через эту команду
admin_site = AdminDashboard(name='myadmin')


# Регистрируем модели с кастомизацией для дашборда
@admin.register(Product, site=admin_site)
class DashboardProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'available')



@admin.register(Order, site=admin_site)
class DashboardOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_price', 'status', 'created')
    list_filter = ('status', 'created')


