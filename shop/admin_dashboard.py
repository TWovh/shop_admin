from django.db.models.functions import TruncDate
from django.http import HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import make_aware, now
from django.views.decorators.csrf import csrf_exempt

from shop.models import Order as ShopOrder
from .models import Product, Category, Cart, CartItem, User, NovaPoshtaSettings, ProductImage, OrderItem, PaymentSettings, Payment
from django.contrib import admin
from django.urls import reverse, path
from django.db.models import F, DecimalField, Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.paginator import Paginator
from django.template.response import TemplateResponse
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.models import LogEntry
from django.contrib import messages
from django import forms
from .utils import test_payment_connection



class AdminDashboard(admin.AdminSite):
    site_header = "Панель управления"
    site_title = "Админка"
    index_title = "Добро пожаловать в админку"

    def has_permission(self, request):
        return request.user.is_active and request.user.is_authenticated

    def no_permission(self, request):
        context = self.each_context(request)
        context.update({
            'title': 'Доступ запрещен',
            'user_role': getattr(request.user, 'role', 'UNKNOWN'),
        })
        return TemplateResponse(request, 'admin/no_permission.html', context, status=403)

    def get_dashboard_stats(self):
        thirty_days_ago = timezone.now() - timedelta(days=30)

        sales_data = ShopOrder.objects.filter(created__gte=thirty_days_ago)
        sales_chart = sales_data.annotate(
            date=TruncDate('created')
        ).values('date').annotate(
            total=Sum('total_price')
        ).order_by('date')

        top_products = Product.objects.annotate(
            order_count=Count('orderitem'),
            revenue=Sum(
                F('orderitem__price') * F('orderitem__quantity'),
                output_field=DecimalField()
            )
        ).order_by('-order_count')[:5]

        total_stats = ShopOrder.objects.aggregate(
            total_sales=Sum('total_price'),
            avg_order=Avg('total_price')
        )

        return {
            'sales_labels': [item['date'].strftime('%Y-%m-%d') for item in sales_chart],
            'sales_values': [float(item['total']) for item in sales_chart],
            'top_products': top_products,
            'total_sales': total_stats['total_sales'] or 0,
            'avg_order': total_stats['avg_order'] or 0,
            'product_count': Product.objects.count(),
            'user_count': User.objects.count(),
        }

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('statistics/', self.admin_view(self.statistics_view), name='statistics'),
        ]
        return custom_urls + urls

    def index(self, request, extra_context=None):
        if getattr(request, 'user_role', '') not in ['ADMIN', 'STAFF']:
            return self.no_permission(request)

        stats = self.get_dashboard_stats()
        extra_context = extra_context or {}
        extra_context.update({
            'total_sales': stats['total_sales'],
            'product_count': stats['product_count'],
            'top_products': stats['top_products'],
            'sales_chart': {
                'labels': stats['sales_labels'],
                'data': stats['sales_values']
            },
        })
        return super().index(request, extra_context)

    def statistics_view(self, request):
        # Инициализируем переменные
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        start_dt = end_dt = None

        # Базовый QuerySet по заказам
        orders_qs = ShopOrder.objects.all()

        # Фильтрация по датам, если заданы
        if start_date:
            try:
                start_dt = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
                orders_qs = orders_qs.filter(created__gte=start_dt)
            except ValueError:
                messages.error(request, "Неверный формат начала периода")
        if end_date:
            try:
                end_dt = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))
                orders_qs = orders_qs.filter(created__lte=end_dt)
            except ValueError:
                messages.error(request, "Неверный формат окончания периода")

        # Подсчёт основных метрик
        total_sales = avg_order = orders_count = 0
        product_sales_by_day = []
        if start_dt and end_dt:
            total_sales = orders_qs.aggregate(total=Sum('total_price'))['total'] or 0
            avg_order = orders_qs.aggregate(avg=Avg('total_price'))['avg'] or 0
            orders_count = orders_qs.count()

            product_sales_by_day = (
                OrderItem.objects
                .filter(order__created__range=(start_dt, end_dt))
                .annotate(date=TruncDate('order__created'))
                .values('product__name', 'date')
                .annotate(
                    total=Sum(
                        F('price') * F('quantity'),
                        output_field=DecimalField()
                    )
                )
                .order_by('date')
            )

        # Пагинация списка заказов
        paginator = Paginator(orders_qs.order_by('-created'), 25)
        page_obj = paginator.get_page(request.GET.get('page'))

        # Статистика по категориям
        categories_stats = (
            Category.objects
            .annotate(total_sales=Sum('products__orderitem__price'))
            .exclude(total_sales__isnull=True)
            .order_by('-total_sales')
        )

        # Статистика платежей за последние 30 дней
        recent_payments = (
            Payment.objects
            .filter(created_at__gte=now() - timedelta(days=30))
            .values('status')
            .annotate(count=Count('id'), total=Sum('amount'))
        )
        STATUS_DISPLAY = dict(Payment.STATUS_CHOICES)
        payment_stats = [
            {
                'status': row['status'],
                'display': STATUS_DISPLAY.get(row['status'], row['status']),
                'count': row['count'],
                'total': row['total'] or 0
            }
            for row in recent_payments
        ]
        overall_payment_total = Payment.objects.aggregate(total=Sum('amount'))['total'] or 0

        # Сбор контекста и рендер
        context = self.each_context(request)
        context.update({
            'title': 'Статистика продаж',
            'start_date': start_date,
            'end_date': end_date,
            'total_sales': total_sales,
            'avg_order': avg_order,
            'orders_count': orders_count,
            'page_obj': page_obj,
            'recent_orders': orders_qs[:10],
            'product_sales_by_day': product_sales_by_day,
            'categories_stats': categories_stats,
            'payment_stats': payment_stats,
            'payment_total_30d': sum(item['total'] for item in payment_stats),
            'overall_payment_total': overall_payment_total,
        })

        return TemplateResponse(request, 'admin/statistics.html', context)

    def get_app_list(self, request, app_label=None):
        from django.urls import NoReverseMatch

        app_list = [
            {
                'name': 'Товары',
                'app_label': 'products',
                'models': [
                    {'name': 'Продукты', 'admin_url': reverse('myadmin:shop_product_changelist')},
                    {'name': 'Категории', 'admin_url': reverse('myadmin:shop_category_changelist')},
                ]
            },
            {
                'name': 'Клиенты',
                'app_label': 'clients',
                'models': [
                    {'name': 'Пользователи', 'admin_url': reverse('myadmin:shop_user_changelist')},
                ]
            },
            {
                'name': 'Заказы',
                'app_label': 'orders',
                'models': [
                    {'name': 'Заказы', 'admin_url': reverse('myadmin:shop_order_changelist')},
                    {'name': 'Корзины пользователей', 'admin_url': reverse('myadmin:shop_cart_changelist')},
                    {'name': 'История Платежей', 'admin_url': reverse('myadmin:shop_payment_changelist')},
                ]
            },
            {
                'name': 'Настройки АПИ',
                'app_label': 'settings',
                'models': [
                    {'name': 'Настройки платежных систем', 'admin_url': reverse('myadmin:shop_paymentsettings_changelist')},
                    {'name': 'Настройки Новой Почты', 'admin_url': reverse('myadmin:shop_novaposhtasettings_changelist')},
                ]
            },
            {
                'name': 'Аналитика',
                'app_label': 'analytics',
                'models': [
                    {'name': 'Статистика', 'admin_url': reverse('myadmin:statistics')},
                ]
            },
        ]

        # Log Entries — только ADMIN
        if getattr(request, 'user_role', '') == 'ADMIN':
            try:
                app_list.append({
                    'name': 'Система',
                    'app_label': 'admin',
                    'models': [
                        {'name': 'Log entries', 'admin_url': reverse('admin:admin_logentry_changelist')},
                    ]
                })
            except NoReverseMatch:
                pass

        return app_list


admin_site = AdminDashboard(name='myadmin')


class RoleBasedAdmin(admin.ModelAdmin):
    roles_with_access = ['ADMIN', 'STAFF']

    def has_module_permission(self, request):
        return self.has_permission(request)

    def has_permission(self, request):
        return (
                request.user.is_authenticated and
                request.user_role in ['ADMIN', 'STAFF']
        )

class InvoiceFilter(admin.SimpleListFilter):
    title = 'Инвойс'
    parameter_name = 'invoice'

    def lookups(self, request, model_admin):
        from shop.models import Payment
        invoices = Payment.objects.filter(status='paid').values_list('external_id', flat=True).distinct()
        return [(inv, inv) for inv in invoices if inv]

    def queryset(self, request, queryset):
        value = self.value()
        if value:
            return queryset.filter(payments__external_id=value)
        return queryset

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_main')
    readonly_fields = ()
    can_delete = True

@admin.register(Product, site=admin_site)
class DashboardProductAdmin(RoleBasedAdmin):
    inlines = [ProductImageInline]
    list_display = ['name', 'price', 'available', 'created']
    list_filter = ('category', 'available')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user_role in {'ADMIN', 'STAFF'}

    def has_change_permission(self, request, obj=None):
        return request.user_role in ['ADMIN', 'STAFF']

    def has_delete_permission(self, request, obj=None):
        return request.user_role == 'ADMIN'


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1  # количество пустых строк
    min_num = 1  # минимум 1 товар
    fields = ('product', 'quantity', 'price')
    autocomplete_fields = ['product']

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "product":
            formfield.widget.can_add_related = False
        return formfield

    class Media:
        js = [
            'admin/js/jquery.init.js',  # <-- это нужно первым
            'admin/js/orderitem_auto_price.js',  # <-- ваш скрипт
        ]

@admin.register(ShopOrder, site=admin_site)
class DashboardOrderAdmin(admin.ModelAdmin):
    change_form_template = "admin/shop/order/change_form.html"
    add_form_template = "admin/shop/order/add_form.html"

    def get_changeform_template(self, request, obj=None, **kwargs):
        return "admin/shop/order/change_form.html"

    def add_view(self, request, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['is_add_view'] = True
        return super().add_view(request, form_url, extra_context=extra_context)

    list_display = [
        'id',
        'view_link',
        'user',
        'status_dropdown',
        'payment_status_badge',
        'delivery_type',
        'total_price_display',
        'delivery_method',
        'invoice_info',
        'created'
    ]
    list_filter = ['status', 'payment_status', 'delivery_type', 'delivery_method']
    readonly_fields = ['total_price', 'created', 'updated']
    search_fields = ['id', 'user__email', 'payments__external_id', 'delivery_type', 'delivery_method']
    inlines = [OrderItemInline]
    actions = ['mark_cod_paid', 'mark_cod_rejected']

    fieldsets = (
        (None, {
            'fields': ('user', 'status', 'payment_status', 'delivery_type', 'delivery_method')
        }),
        ('Контакты', {
            'fields': ('city', 'address', 'phone', 'email')
        }),
        ('Дополнительно', {
            'fields': ('comments',),
            'classes': ('collapse',)
        }),
        ('Служебные поля', {
            'fields': ('total_price', 'created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    def status_dropdown(self, obj):
        options = "".join(
            f"<option value='{key}' {'selected' if obj.status == key else ''}>{label}</option>"
            for key, label in ShopOrder.STATUS_CHOICES
        )

        return format_html(
            f"""
            <select data-order-id="{obj.id}" class="status-dropdown" style="min-width: 140px;">
                {options}
            </select>
            """
        )

    status_dropdown.short_description = "Статус заказа"

    class Media:
        js = ('admin/js/order_status_update.js',)

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                'update-status/',
                self.admin_site.admin_view(self.update_status),
                name='order_update_status',
            ),
        ]
        return custom_urls + urls

    @method_decorator(csrf_exempt, name='dispatch')
    def update_status(self, request):
        if request.method == 'POST' and request.user.is_staff:
            order_id = request.POST.get('order_id')
            new_status = request.POST.get('new_status')
            if not order_id or not new_status:
                return JsonResponse({'success': False, 'error': 'Missing data'}, status=400)

            try:
                order = ShopOrder.objects.get(pk=order_id)
                if new_status in dict(ShopOrder.STATUS_CHOICES):
                    order.status = new_status
                    order.save()
                    return JsonResponse({'success': True, 'status': order.get_status_display()})
                return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
            except ShopOrder.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Order not found'}, status=404)
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    def get_queryset(self, request):
        self.request = request  # сохраняем для CSRF
        return super().get_queryset(request)

    def invoice_info(self, obj):
        payment = obj.payments.filter(status='paid').last()
        if payment:
            return format_html(
                '<div><b>{}</b><br><small style="color: #666;">{}</small></div>',
                payment.external_id,
                payment.get_payment_system_display()
            )
        return '—'

    invoice_info.short_description = 'Инвойс / Система'

    def row_actions(self, obj):
        buttons = []
        if obj.delivery_type == 'cod' and obj.payment_status != 'paid':
            pay_url = (
                    reverse('admin:shop_order_changelist') +
                    f'?action=mark_cod_paid&select_across=0&_selected_action={obj.pk}'
            )
            buttons.append(f'<a class="button" href="{pay_url}">Оплачен</a>')
        if obj.delivery_type == 'cod' and obj.payment_status != 'refunded':
            cancel_url = (
                    reverse('admin:shop_order_changelist') +
                    f'?action=mark_cod_rejected&select_across=0&_selected_action={obj.pk}'
            )
            buttons.append(f'<a class="button" href="{cancel_url}">Отменён</a>')
        return format_html(' '.join(buttons)) if buttons else '-'

    row_actions.short_description = 'Статус наложки'
    row_actions.allow_tags = True

    def total_price_display(self, obj):
        return f"{obj.total_price:.2f} Грн"

    total_price_display.short_description = 'Сумма заказа'
    total_price_display.admin_order_field = 'total_price'

    @admin.action(description="Отметить как оплачен (наложка)")
    def mark_cod_paid(self, request, queryset):
        updated = 0
        for order in queryset:
            if order.delivery_type == 'cod' and order.payment_status != 'paid':
                order.payment_status = 'paid'
                order.status = 'completed'
                order.save()
                updated += 1
        self.message_user(request, f"Обновлено {updated} заказов как «Оплачен».", messages.SUCCESS)

    @admin.action(description="Отметить как не оплачено (отмена наложки)")
    def mark_cod_rejected(self, request, queryset):
        updated = 0
        for order in queryset:
            if order.delivery_type == 'cod' and order.payment_status != 'refunded':
                order.payment_status = 'refunded'
                order.status = 'cancelled'
                order.save()
                updated += 1
        self.message_user(request, f"Обновлено {updated} заказов как «Отменён».", messages.WARNING)

    @admin.action(description="Создать ТТН через Nova Poshta")
    def create_ttn_action(self, request, queryset):
        from .views import create_ttn

        settings_qs = NovaPoshtaSettings.objects.filter(is_active=True)

        if settings_qs.count() != 1:
            self.message_user(request, "Настройки Новой Почты не найдены или их несколько", level=messages.ERROR)
            return

        settings = settings_qs.get()

        if not settings.auto_create_ttn:
            self.message_user(request, "Автосоздание ТТН отключено в настройках", level=messages.WARNING)
            return

        success_count = 0
        fail_count = 0

        for order in queryset:
            if order.delivery_method != 'nova_poshta':
                continue

            result = create_ttn(order, settings=settings)

            if result.get("success"):
                success_count += 1
            else:
                fail_count += 1
                msg = result.get("message", "Неизвестная ошибка")
                self.message_user(request, f"Заказ #{order.id}: {msg}", level=messages.WARNING)

        if success_count:
            self.message_user(request, f"Создано ТТН: {success_count}", level=messages.SUCCESS)
        if fail_count and not success_count:
            self.message_user(request, f"Не удалось создать ТТН ни для одного заказа", level=messages.ERROR)


    def payment_status_badge(self, obj):
        colors = {
            'unpaid': 'gray',
            'paid': 'green',
            'pending': 'orange',
            'refunded': 'blue'
        }
        return format_html(
            '<span style="background:{}; color:white; padding:2px 6px; border-radius:4px">{}</span>',
            colors.get(obj.payment_status, 'gray'),
            obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Статус оплаты'
    payment_status_badge.admin_order_field = 'payment_status'

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST' and 'new_status' in request.POST:
            obj = self.get_object(request, object_id)
            if obj:
                new_status = request.POST.get('new_status')
                if new_status in dict(ShopOrder.STATUS_CHOICES):
                    obj.status = new_status
                    obj.save()
                    self.message_user(request, f"Статус обновлён на «{obj.get_status_display()}».")
        return super().changeform_view(request, object_id, form_url, extra_context)

    def payment_actions(self, obj):
        if obj.id and obj.payment_status == 'unpaid':
            return format_html(
                '<a href="{}" class="button">Создать платеж</a>',
                reverse('create-payment', args=[obj.id])
            )
        return '-'
    payment_actions.short_description = 'Действия'

    def view_link(self, obj):
        url = reverse('admin:shop_order_change', args=[obj.pk])
        return format_html('<a class="button" href="{}">Просмотр</a>', url)

    view_link.short_description = 'Подробнее'
    view_link.allow_tags = True

    def save_model(self, request, obj, form, change):
        # Сохраняем сам объект заказа без попытки считать инлайны
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        # 1) Сначала сохраняем все инлайны (OrderItem)
        super().save_related(request, form, formsets, change)

        # 2) Пересчитываем итоговую сумму по уже сохранённым инлайнам
        total = sum(
            item.price * item.quantity
            for item in form.instance.order_items.all()
        )

        # 3) Обновляем поле total_price в базе
        ShopOrder.objects.filter(pk=form.instance.pk).update(total_price=total)

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
    list_display = ('email', 'is_staff', 'is_active')  # Используем get_role_display
    list_filter = ('role', 'is_staff', 'is_active')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['role'].required = True  # Пример дополнительной настройки
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
    readonly_fields = ('total_price',)

    def total_price(self, obj):
        return obj.total_price
    total_price.short_description = 'Сумма'


@admin.register(LogEntry, site=admin_site)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['action_time', 'user', 'content_type', 'object_repr', 'action_flag']
    list_filter = ['action_flag', 'content_type']
    search_fields = ['user__email', 'object_repr', 'change_message']
    readonly_fields = list_display
    date_hierarchy = 'action_time'


class PaymentSettingsForm(forms.ModelForm):
    api_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True),
        label="API ключ",
        help_text="Оставьте пустым, чтобы не изменять текущее значение"
    )
    secret_key = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True),
        label="Секретный ключ",
        help_text="Оставьте пустым, чтобы не изменять текущее значение"
    )
    webhook_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True),
        label="Секрет вебхука",
        help_text="Оставьте пустым, чтобы не изменять текущее значение"
    )

    class Meta:
        model = PaymentSettings
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')  # Получаем до super
        super().__init__(*args, **kwargs)
        if instance:
            if instance.api_key:
                self.fields['api_key'].widget.attrs['placeholder'] = '**********'
            if instance.secret_key:
                self.fields['secret_key'].widget.attrs['placeholder'] = '**********'
            if instance.webhook_secret:
                self.fields['webhook_secret'].widget.attrs['placeholder'] = '**********'

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.cleaned_data.get('api_key', '').strip():
            instance.api_key = self.cleaned_data['api_key'].strip()
        if self.cleaned_data.get('secret_key', '').strip():
            instance.secret_key = self.cleaned_data['secret_key'].strip()
        if self.cleaned_data.get('webhook_secret', '').strip():
            instance.webhook_secret = self.cleaned_data['webhook_secret'].strip()

        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        api_key = cleaned_data.get("api_key") or self.instance._api_key
        secret_key = cleaned_data.get("secret_key") or self.instance._secret_key
        webhook_secret = cleaned_data.get("webhook_secret") or self.instance._webhook_secret
        payment_system = cleaned_data.get("payment_system") or self.instance.payment_system

        if not api_key:
            raise forms.ValidationError("API ключ не может быть пустым.")
        if not secret_key:
            raise forms.ValidationError("Секретный ключ не может быть пустым.")
        if payment_system == 'stripe' and not webhook_secret:
            raise forms.ValidationError("Webhook секрет обязателен для Stripe.")
        return cleaned_data


@admin.register(PaymentSettings, site=admin_site)
class PaymentSettingsAdmin(admin.ModelAdmin):
    form = PaymentSettingsForm
    list_display = ('payment_system', 'is_active', 'is_sandbox', 'get_created_at')
    list_editable = ('is_active', 'is_sandbox')
    actions = ['test_connection']

    fieldsets = (
        (None, {
            'fields': ('payment_system', 'is_active', 'is_sandbox')
        }),
        ('API Ключи', {
            'fields': ('api_key', 'secret_key', 'webhook_secret'),
            'description': 'Получить ключи можно в личном кабинете платёжной системы. Видны только при редактировании'
        }),
    )

    def get_created_at(self, obj):
        return obj.created_at.strftime("%d.%m.%Y %H:%M")

    get_created_at.admin_order_field = 'created_at'
    get_created_at.short_description = 'Создан'

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "payment_system":
            kwargs["choices"] = [
                choice for choice in db_field.choices if choice[0] != "manual"
            ]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def test_connection(self, request, queryset):
        for settings in queryset:
            try:
                success, message = test_payment_connection(settings)
            except Exception as e:
                success = False
                message = f"Ошибка: {str(e)}"
            level = messages.SUCCESS if success else messages.ERROR
            self.message_user(request, f"{settings.get_payment_system_display()}: {message}", level)

    test_connection.short_description = "Проверить подключение к платёжной системе"



@admin.register(Payment, site=admin_site)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_link', 'payment_system', 'amount', 'status', 'created_at')
    list_filter = ('payment_system', 'status', 'created_at')
    search_fields = ('order__id', 'external_id')
    readonly_fields = ('created_at', 'updated_at', 'raw_response')

    def order(self, obj):
        return obj.order.id
    order.short_description = 'Заказ'

    def order_link(self, obj):
        url = reverse('myadmin:shop_order_change', args=[obj.order.id])
        return format_html('<a href="{}">Заказ #{}</a>', url, obj.order.id)

    order_link.short_description = 'Заказ'




class NovaPoshtaSettingsForm(forms.ModelForm):
    api_key = forms.CharField(
        widget=forms.PasswordInput(render_value=True),
        required=False,
        label="API ключ",
        help_text="Оставьте пустым, чтобы не менять"
    )

    class Meta:
        model = NovaPoshtaSettings
        fields = [
            'api_key',
            'sender_city_ref',
            'default_sender_name',
            'senders_phone',
            'auto_create_ttn',
            'is_active'
        ]

@admin.register(NovaPoshtaSettings, site=admin_site)
class NovaPoshtaSettingsAdmin(admin.ModelAdmin):
    form = NovaPoshtaSettingsForm
    list_display = ['masked_api_key', 'sender_city_ref', 'default_sender_name', 'senders_phone',
                    'auto_create_ttn', 'default_weight', 'default_seats_amount',
                    'updated_at']
    readonly_fields = ['updated_at']


    def masked_api_key(self, obj):
        if obj.api_key:
            return '*****'  # или можно показывать первые 4 символа + ****
            # Например: return obj.api_key[:4] + '****'
        return '-'

    masked_api_key.short_description = 'API ключ'

    def has_add_permission(self, request):
        return not NovaPoshtaSettings.objects.exists()