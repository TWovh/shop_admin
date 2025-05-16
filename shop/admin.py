from django.contrib import admin
from .models import Category, Product
from django.urls import reverse
from django import forms
from .models import Product, Category

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
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'price', 'available', 'category', 'image_preview')
    list_filter = ('available', 'created', 'updated', 'category')
    list_editable = ('price', 'available')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('image_preview',)
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

