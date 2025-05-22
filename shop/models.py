from django.db import models, transaction
from django.urls import reverse
from django.db.models import Index, Sum
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    ROLES = (
        ('ADMIN', 'Администратор'),
        ('STAFF', 'Менеджер'),
        ('USER', 'Пользователь'),
    )
    role: str = models.CharField(
        max_length=5,
        choices=ROLES,
        default='USER',
        verbose_name='Роль'
    )

    username = None
    email = models.EmailField(_('email address'), unique=True)
    phone = models.CharField(max_length=20, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        permissions = [
            ('full_access', 'Full admin access'),
            ('staff_access', 'Staff access'),
        ]

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith(('pbkdf2_sha256$', 'bcrypt$')):
            validate_password(self.password)
        super().save(*args, **kwargs)

class Category(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ('name',)
        verbose_name = 'category'
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_list_by_category', args=[self.slug])


class Product(models.Model):
    category = models.ForeignKey(Category, related_name='products', on_delete=models.CASCADE)
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True, verbose_name="Изображение")

    def image_preview(self):
        if self.image:
            return mark_safe(f'<img src="{self.image.url}" width="150" />')
        return "Нет изображения"

    image_preview.short_description = "Превью"
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [
            ('view_dashboard', 'Can view admin dashboard'),
            ('manage_cart', 'Can manage carts'),
        ]
        ordering = ('name',)
        indexes = [
            Index(fields=['id', 'slug']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.id, self.slug])


class Cart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Пользователь'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        ordering = ['-updated_at']

    def __str__(self):
        return f"Корзина {self.user.username if self.user else 'анонима'}"

    @property
    def total_price(self):
        """Суммарная стоимость всех товаров в корзине с кэшированием"""
        return sum(item.total_price for item in self.items.all())

    @property
    def items_count(self):
        """Общее количество товаров в корзине"""
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0

    def create_order(self, shipping_address, phone, email, comments=''):
        """
        Создает заказ из корзины с валидацией
        """
        if not self.items.exists():
            raise ValueError("Нельзя создать заказ из пустой корзины")

        with transaction.atomic():
            order = Order.objects.create(
                user=self.user,
                total_price=self.total_price,
                shipping_address=shipping_address,
                phone=phone,
                email=email,
                comments=comments,
                status='new'
            )

            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                ) for item in self.items.all()
            ]

            OrderItem.objects.bulk_create(order_items)
            self.items.all().delete()

        return order

    def clear(self):
        """Очистка корзины"""
        self.items.all().delete()
        self.save()


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items',
        verbose_name='Товар'
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name='Количество'
    )
    added_at = models.DateTimeField(
        default=timezone.now,
        verbose_name='Дата добавления'
    )

    class Meta:
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'
        unique_together = ['cart', 'product']  # Один товар - одна позиция в корзине
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.product.name} x{self.quantity} (в корзине {self.cart.user.username})"

    @property
    def total_price(self):
        return self.product.price * self.quantity

    def clean(self):
        if self.product.available is False:
            raise ValidationError("Нельзя добавить недоступный товар в корзину")

        if self.quantity > 100:  # Максимальное количество
            raise ValidationError("Слишком большое количество товара")

    def save(self, *args, **kwargs):
        """Переопределение save с валидацией"""
        self.full_clean()
        super().save(*args, **kwargs)

class Order(models.Model):
    PROTECTED_FIELDS = ['total_price', 'user']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._meta.get_field('total_price').editable = False

    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    comments = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created']),
        ]
        ordering = ('-created',)
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def __str__(self):
        return f"Заказ #{self.id} ({self.get_status_display()})"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.price * self.quantity





