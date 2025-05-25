from .models import Product, Category, Order, Cart, CartItem, User
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
from django.contrib.auth.models import User, Group, AbstractUser
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin.forms import AdminAuthenticationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.admin.models import LogEntry, CHANGE, ADDITION
from django.contrib.contenttypes.models import ContentType
import json
from django.http import HttpRequest, HttpResponse
from .types import AuthenticatedRequest, AuthRequest

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

    def admin_view(self, view, cacheable=False):
        from functools import wraps

        @wraps(view)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if not hasattr(request, 'POST'):
                request.POST = getattr(request, 'POST', {})

            if not request.user.is_authenticated:
                return self.login(request)

            if not hasattr(request.user, 'role') or request.user.role not in ['ADMIN', 'STAFF']:
                return self.no_permission(request)

            return view(request, *args, **kwargs)

        return super().admin_view(wrapper, cacheable)

    def has_permission(self, request):
        return (
                request.user.is_authenticated and
                hasattr(request.user, 'role') and
                request.user.role in ['ADMIN', 'STAFF']
        )


    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label)

        # Проверка прав перед добавлением разделов
        if request.user.role in ['ADMIN', 'STAFF']:
            for app in app_list:
                if app['app_label'] == 'auth':
                    app['models'].append({
                        'name': 'Статистика',
                        'object_name': 'statistics',
                        'admin_url': reverse('myadmin:statistics'),
                        'view_only': True,
                    })
                    break

        if request.user.role in ['ADMIN', 'STAFF']:
            app_list.append({
                'name': 'Корзины',
                'app_label': 'carts',
                'models': [
                    {
                        'name': 'Корзины',
                        'object_name': 'cart',
                        'admin_url': reverse('admin:shop_cart_changelist'),
                    },
                    {
                        'name': 'Элементы корзины',
                        'object_name': 'cartitem',
                        'admin_url': reverse('admin:shop_cartitem_changelist'),
                    }
                ]
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=ContentType.objects.get_for_model(obj).pk,
            object_id=obj.pk,
            object_repr=str(obj),
            action_flag=CHANGE if change else ADDITION,
            change_message=json.dumps(form.changed_data)
        )


    def no_permission(self, request: AuthenticatedRequest) -> HttpResponse:
        context = self.each_context(request)
        context.update({
            'title': 'Доступ запрещен',
            'user_role': request.user.get_role_display(),
        })
        return TemplateResponse(
            request,
            'admin/no_permission.html',
            context,
            status=403
        )

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

    def index(self, request: AuthenticatedRequest, extra_context=None) -> HttpResponse:

        if request.user.role not in ['ADMIN', 'STAFF']:
            return self.no_permission(request)

        extra_context = extra_context or {}
        stats = self.get_dashboard_stats()

        extra_context.update({
            'api_links': [
                {
                    'name': 'Список товаров',
                    'url': reverse('product-list'),
                    'method': 'GET'
                },
                {
                    'name': 'Список категорий',
                    'url': reverse('category-list'),
                    'method': 'GET'
                },

                {
                    'name': 'Детали товара',
                    'url': '/api/products/1/',  # Или используйте reverse с параметрами
                    'method': 'GET'
                },
                {
                    'name': 'Добавить в корзину',
                    'url': reverse('add-to-cart'),
                    'method': 'POST'
                }
            ],
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
        try:
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
        except Exception as e:
            return self.message_user(request, f"Ошибка: {str(e)}", level='error')
# Замена админки через эту команду
admin_site = AdminDashboard(name='myadmin')


class RoleBasedAdmin(admin.ModelAdmin):
    roles_with_access = ['ADMIN', 'STAFF']

    def has_module_permission(self, request):
        return self.has_permission(request)

    def has_permission(self, request):
        return (
                request.user.is_authenticated and
                request.user.role in ['ADMIN', 'STAFF']
        )

@admin.register(Product, site=admin_site)
class DashboardProductAdmin(RoleBasedAdmin):
    list_display = ('name', 'price', 'category', 'available')
    list_filter = ('category', 'available')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.role in {'ADMIN', 'STAFF'}

    def has_change_permission(self, request, obj=None):
        return request.user.role in ['ADMIN', 'STAFF']

    def has_delete_permission(self, request, obj=None):
        return request.user.role == 'ADMIN'

@admin.register(Order, site=admin_site)
class DashboardOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_price', 'status', 'created')
    list_filter = ('status', 'created')
    search_fields = ('user__username', 'id')



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
    list_display = ('name', 'slug', 'product_count')
    prepopulated_fields = {'slug': ('name',)}

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = 'Товаров'

# Администратор (полные права)
@admin.register(User, site=admin_site)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'get_role_display', 'is_staff', 'is_active')  # Используем get_role_display
    list_filter = ('role', 'is_staff', 'is_active')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['role'].role = 'role'  # Явное указание для IDE
        return form

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'phone')}),
        ('Права доступа', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Даты', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )

    ordering = ('email',)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['role'].required = True  # Пример дополнительной настройки
        return form



# Сотрудник (ограниченные права)
class StaffAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        user = request.user
        if hasattr(user, 'role'):
            return user.role == 'STAFF'
        return False

    def has_add_permission(self, request):
        user = request.user
        if hasattr(user, 'role'):
            return user.role == 'STAFF'
        return False

    def has_change_permission(self, request, obj=None):
        user = request.user
        if hasattr(user, 'role'):
            return user.role == 'STAFF'
        return False

    def has_delete_permission(self, request, obj=None):
        return False  # Сотрудники не могут удалять

# Обычные пользователи не видят админку


@admin.register(Cart, site=admin_site)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at', 'items_count', 'total_price')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('total_price', 'items_count')
    raw_id_fields = ('user',)

    def items_count(self, obj):
        return obj.items.count()
    items_count.short_description = 'Количество товаров'

    def total_price(self, obj):
        return sum(item.total_price for item in obj.items.all())
    total_price.short_description = 'Общая сумма'

@admin.register(CartItem, site=admin_site)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity', 'total_price')
    list_filter = ('cart__user',)
    search_fields = ('product__name', 'cart__user__username')
    raw_id_fields = ('cart', 'product')

    def total_price(self, obj):
        return obj.total_price
    total_price.short_description = 'Сумма'


class CustomAdminAuthForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.role not in ['ADMIN', 'STAFF']:
            raise ValidationError("Доступ запрещен.")

@admin.register(LogEntry, site=admin_site)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['action_time', 'user', 'content_type', 'object_repr', 'action_flag']
    list_filter = ['action_flag', 'content_type']
    search_fields = ['user__email', 'object_repr', 'change_message']
    readonly_fields = list_display
    date_hierarchy = 'action_time'