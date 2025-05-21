from .models import Product, Order, Category, OrderItem
from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from django.http import Http404
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin


class AdminDashboard(admin.AdminSite):
    index_template = 'admin/dashboard.html'
    site_header = 'Панель управления магазином'
    site_title = 'Администрирование магазина'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('statistics/', self.admin_view(self.statistics_view), name='statistics'),
            path('api/cart/add/', self.admin_view(self.redirect_to_api_cart_add), name='api-cart-add'),

        ]
        return custom_urls + urls

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)
        for app in app_list:
            if app['app_label'] == 'auth':
                app['models'].append({
                    'name': 'Статистика',
                    'object_name': 'statistics',
                    'admin_url': reverse('myadmin:statistics'),
                    'view_only': True,
                })
        return app_list

    def add_product(self, request):
        if request.method == 'POST':
            return HttpResponseRedirect(reverse('myadmin:shop_product_changelist'))
        return TemplateResponse(request, 'admin/add_product.html', self.each_context(request))

    def add_category(self, request):
        from django import forms
        from django.contrib import messages

        class CategoryForm(forms.ModelForm):
            class Meta:
                model = Category
                fields = ['name', 'slug']
                widgets = {
                    'name': forms.TextInput(attrs={'class': 'vTextField'}),
                    'slug': forms.TextInput(attrs={'class': 'vTextField'}),
                }

        if request.method == 'POST':
            form = CategoryForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Категория успешно добавлена')
                return HttpResponseRedirect(reverse('myadmin:shop_category_changelist'))

        else:
            form = CategoryForm()

        context = {
            'form': form,
            'title': 'Добавить категорию',
            **self.each_context(request),
        }
        return TemplateResponse(request, 'admin/add_category.html', context)

    def quick_orders(self, request):
        recent_orders = Order.objects.order_by('-created')[:10]
        return TemplateResponse(request, 'admin/quick_orders.html', {
            'recent_orders': recent_orders,
            **self.each_context(request)
        })

    def redirect_to_api_products(self, request):
        return redirect(reverse('api-products'))  # Проверить есть ли он юрлс

    def redirect_to_api_product_detail(self, request, pk):
        return redirect(reverse('api-product-detail', args=[pk]))

    def redirect_to_api_cart_add(self, request):
        return redirect(reverse('api-cart-add'))

    def get_dashboard_stats(self):

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
                order_count=Count('orderitem'),  # Количество заказов для товара
                revenue=Sum('orderitem__price')  # Общая выручка по товару
            )
            .order_by('-order_count')[:5]
        )

        total_stats = Order.objects.aggregate(
            total_sales=Sum('total_price'),
            avg_order=Avg('total_price')
        )
        from django.contrib.auth.models import User
        user_stats = {
            'user_count': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count()
        }

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

        extra_context['api_links'] = [
            {
                'name': 'Список товаров',
                'url': reverse('myadmin:api-products'),
                'method': 'GET'
            },
            {
                'name': 'Детали товара',
                'url': reverse('myadmin:api-product-detail', args=[0]).replace('0', '{id}'),
                'method': 'GET'
            },
            {
                'name': 'Добавить в корзину',
                'url': reverse('myadmin:api-cart-add'),
                'method': 'POST'
            }
        ]

        extra_context.update({
            'total_sales': stats['total_sales'],
            'product_count': stats['product_count'],
            'top_products': stats['top_products'],
            'sales_chart': {
                'labels': stats['sales_labels'],
                'data': stats['sales_values']
            }
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
            .annotate(total_sales=Sum('products__orderitem__price'))
            .exclude(total_sales=None)
            .order_by('-total_sales')
        )

        context = {
            'total_sales': orders.aggregate(total=Sum('total_price'))['total'] or 0,
            'orders_count': orders.count(),
            'recent_orders': orders.order_by('-created')[:10],
            'categories_stats': categories_stats,
            **self.each_context(request),
            'title': 'Статистика продаж',
        }
        return TemplateResponse(request, 'admin/statistics.html', context)

# Замена админки через эту команду
admin_site = AdminDashboard(name='myadmin')


# Регистрируем модели с кастомизацией для дашборда
@admin.register(Product, site=admin_site)
class DashboardProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'available')
    list_filter = ('category', 'available')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    def quick_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Edit</a> '
            '<a class="button" href="{}" style="background:#4CAF50">Copy</a>',
            reverse('myadmin:shop_product_change', args=[obj.id]),
            reverse('myadmin:shop_product_copy', args=[obj.id]),
        )

    quick_actions.short_description = 'Действия'

@admin.register(Order, site=admin_site)
class DashboardOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_price', 'status', 'created', 'quick_actions')
    list_filter = ('status', 'created')
    search_fields = ('user__username', 'id')

    def quick_actions(self, obj):
        return format_html(
            '<a class="button" href="{}">Просмотр</a>',
            reverse('myadmin:shop_order_change', args=[obj.id]),
        )
    quick_actions.short_description = ''


def redirect_to_api_cart_add(self, request):
    if request.method == 'POST':
        return redirect(reverse('myadmin:api-cart-add'))

    context = {
        **self.each_context(request),
        'title': 'Добавить в корзину',
        'opts': self._registry[Order].model._meta,
    }
    return render(request, 'admin/cart_add_form.html', context)


@admin.register(Category, site=admin_site)
class DashboardCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count', 'quick_edit')
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = 'Товаров'

    def quick_edit(self, obj):
        return format_html(
            '<a class="button" href="{}">Быстрое редактирование</a>',
            reverse('myadmin:shop_category_change', args=[obj.id]),
        )

    quick_edit.short_description = ''

@admin.register(User, site=admin_site)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')