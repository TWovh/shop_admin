from django.core import signing
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
from decimal import Decimal


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
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Администратор'
        STAFF = 'STAFF', 'Менеджер'
        USER = 'USER', 'Пользователь'

    role: models.CharField = models.CharField(
        max_length=5,
        choices=Role.choices,
        default=Role.USER,
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

    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN

    def is_staff_member(self) -> bool:
        return self.role in [self.Role.ADMIN, self.Role.STAFF]

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
    name = models.CharField(max_length=200, db_index=True, verbose_name="Название")
    slug = models.SlugField(max_length=200, db_index=True, unique=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d', blank=True, verbose_name="Изображение")
    stock = models.IntegerField(default=0)

    def image_preview(self):
        if self.image:
            return mark_safe(f'<img src="{self.image.url}" width="150" />')
        return "Нет изображения"

    image_preview.short_description = "Превью"
    description = models.TextField(blank=True)

    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
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

    def clean(self):
        if self.price <= 0:
            raise ValidationError("Цена должна быть положительной")

class ProductImage(models.Model):
    product = models.ForeignKey('Product', related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Image for {self.product.name}"


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
                address=shipping_address,
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

    def add_product(self, product, quantity=1):
        item, created = CartItem.objects.get_or_create(
            cart=self,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            item.quantity += quantity
            item.save()

        return item

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
        ('completed', 'Завершён'),
        ('cancelled', 'Отменён'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'Не оплачено'),
        ('paid', 'Оплачено'),
        ('pending', 'Ожидает'),
        ('refunded', 'Возврат'),
    ]

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    city = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='unpaid')
    city_ref = models.CharField(max_length=255, blank=True, null=True)
    warehouse_ref = models.CharField(max_length=255, blank=True, null=True)
    delivery_type = models.CharField(
        max_length=20,
        choices=[('prepaid', 'Оплата онлайн'), ('cod', 'Наложенный платеж')],
        default='prepaid'
    )
    comments = models.TextField(blank=True, null=True, max_length=300)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created']),
        ]
        ordering = ('-created',)
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def can_be_modified(self):
        return self.status in ['new', 'processing']

    def calculate_total_price(self):
        return sum(
            (item.product.price * item.quantity for item in self.items.all()),
            Decimal('0.00')
        )

    def update_total_price(self):
        total = Decimal(0)
        for item in self.order_items.all():
            total += item.total_price
        self.total_price = total
        self.save()

    def __str__(self):
        return f"Order #{self.pk}"


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


class PaymentSettings(models.Model):
    PAYMENT_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('portmone', 'Portmone'),
        ('liqpay', 'LiqPay'),
        ('fondy', 'Fondy'),
    ]

    payment_system = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default='stripe',
        verbose_name='Платежная система'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    _api_key = models.CharField(max_length=255, verbose_name='API ключ (зашифрован)', blank=True)
    _secret_key = models.CharField(max_length=255, verbose_name='Секретный ключ (зашифрован)', blank=True)
    _webhook_secret = models.CharField(max_length=255, blank=True, null=True, verbose_name='Секрет вебхука (зашифрован)')

    @property
    def api_key(self):
        return signing.loads(self._api_key) if self._api_key else ""

    @api_key.setter
    def api_key(self, value):
        self._api_key = signing.dumps(value)

    @property
    def secret_key(self):
        return signing.loads(self._secret_key) if self._secret_key else ""

    @secret_key.setter
    def secret_key(self, value):
        self._secret_key = signing.dumps(value)

    @property
    def webhook_secret(self):
        return signing.loads(self._webhook_secret) if self._webhook_secret else ""

    @webhook_secret.setter
    def webhook_secret(self, value):
        self._webhook_secret = signing.dumps(value)

    # Сохраняем оригинальные значения в памяти для админки
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_api_key = self.api_key
        self.__original_secret_key = self.secret_key
        self.__original_webhook_secret = self.webhook_secret

    def save(self, *args, **kwargs):
        # Шифруем только если значение изменилось
        if self.api_key != self.__original_api_key:
            self._api_key = signing.dumps(self.api_key)
        if self.secret_key != self.__original_secret_key:
            self._secret_key = signing.dumps(self.secret_key)
        if self.webhook_secret != self.__original_webhook_secret:
            self._webhook_secret = signing.dumps(self.webhook_secret)

        super().save(*args, **kwargs)
        self.__original_api_key = self.api_key
        self.__original_secret_key = self.secret_key
        self.__original_webhook_secret = self.webhook_secret

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Настройка платежей'
        verbose_name_plural = 'Настройки платежей'

    def clean(self):
        if not self.api_key:
            raise ValidationError("API ключ не может быть пустым.")
        if not self.secret_key:
            raise ValidationError("Секретный ключ не может быть пустым.")
        if self.payment_system == 'stripe' and not self.webhook_secret:
            raise ValidationError("Webhook секрет обязателен для Stripe.")

    def __str__(self):
        return f"{self.get_payment_system_display()} ({'активна' if self.is_active else 'неактивна'})"


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачено'),
        ('failed', 'Ошибка оплаты'),
        ('refunded', 'Возврат'),
    ]
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Пользователь'
    )

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    external_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    raw_response = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        indexes = [
            models.Index(fields=['external_id', 'status']),
        ]

    def __str__(self):
        return f"Платеж #{self.id} для заказа {self.order.id}"



    def save(self, *args, **kwargs):
        if not self.user and self.order and self.order.user:
            self.user = self.order.user
        super().save(*args, **kwargs)


class NovaPoshtaSettings(models.Model):
    api_key = models.CharField(max_length=255, help_text="API ключ my.novaposhta.ua")
    sender_city_ref = models.CharField(max_length=255, blank=True, null=True, help_text="Ref города отправителя")
    default_sender_name = models.CharField(max_length=255, blank=True, null=True, help_text="Имя отправителя по умолчанию")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Настройки Новой Почты"

    def save(self, *args, **kwargs):
        if not self.pk and NovaPoshtaSettings.objects.exists():
            raise ValidationError("Можно создать только одну запись с настройками Новой Почты.")
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Nova Poshta Настройка"
        verbose_name_plural = "Nova Poshta Настройки"