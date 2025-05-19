from django.contrib import admin
from django.urls import reverse
from django import forms
from .models import Product, Category, Order, OrderItem
from shop.admin_dashboard import admin_site

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'cols': 60}),
        }

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)} # генератор людских ссылок при добавлении продукта

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'price', 'available', 'category', 'image_preview')
    list_filter = ('available', 'created', 'updated', 'category')
    list_editable = ('price', 'available')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('image_preview', 'created', 'updated')

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'available')
        }),
        ('Описание и изображение', {
            'fields': ('description', 'image', 'image_preview')
        }),
        ('Метаданные', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )
    actions = ['make_available', 'make_unavailable']

    def make_available(self, request, queryset):
        queryset.update(available=True)

    make_available.short_description = "Сделать выбранные товары доступными"

    def make_unavailable(self, request, queryset):
        queryset.update(available=False)

    make_unavailable.short_description = "Сделать выбранные товары недоступными"

    def view_on_site(self, obj):
        return reverse('product_detail', args=[obj.id, obj.slug])


"""@admin.register(Order, site=admin_site)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'created')
    list_filter = ('status', 'created')
    search_fields = ('id', 'user__username', 'phone')
    readonly_fields = ('created', 'updated', 'total_price')
    fieldsets = (
        (None, {
            'fields': ('user', 'status', 'total_price')
        }),
        ('Информация о доставке', {
            'fields': ('shipping_address', 'phone', 'email')
        }),
        ('Дополнительно', {
            'fields': ('comments', 'created', 'updated'),
            'classes': ('collapse',)
        }),
    )
"""

@admin.register(OrderItem, site=admin_site)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price', 'total_price')
    list_filter = ('order__status',)

    def total_price(self, obj):
        return obj.total_price

    total_price.short_description = 'Общая сумма'
