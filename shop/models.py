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
        """
        Создание пользователя
        """
        if not email:
            raise ValueError('The Email must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        
        if password:
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
        """
        Сохранение пользователя
        """
        # Валидация пароля
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
    stock = models.IntegerField(default=0)
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

    def image_preview(self):
        """Превью изображения для админки"""
        # Получаем главное изображение
        main_image = self.images.filter(is_main=True).first()
        if main_image and main_image.image:
            return mark_safe(f'<img src="{main_image.image.url}" width="150" />')
        
        # Если нет главного, берем первое
        first_image = self.images.first()
        if first_image and first_image.image:
            return mark_safe(f'<img src="{first_image.image.url}" width="150" />')
        
        return "Нет изображения"

    image_preview.short_description = "Превью"

    def clean(self):
        if self.price <= 0:
            raise ValidationError("Цена должна быть положительной")
        super().clean()

    def save(self, *args, **kwargs):
        """
        Сохранение товара
        """
        # Валидация перед сохранением
        self.full_clean()
        super().save(*args, **kwargs)

class ProductImage(models.Model):
    product = models.ForeignKey('Product', related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False, verbose_name="Главная картинка")

    def save(self, *args, **kwargs):
        # Убедиться, что только одно изображение может быть главным
        if self.is_main:
            ProductImage.objects.filter(product=self.product, is_main=True).update(is_main=False)
        
        super().save(*args, **kwargs)

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
        Создает заказ из корзины с валидацией в транзакции
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.items.exists():
            logger.warning(f"Attempted to create order from empty cart for user {self.user.email}")
            raise ValueError("Нельзя создать заказ из пустой корзины")

        try:
            with transaction.atomic():
                logger.info(f"Starting order creation transaction for user {self.user.email}")
                
                # Блокируем корзину для обновления (защита от race conditions)
                cart = Cart.objects.select_for_update().get(id=self.id)
                logger.info(f"Locked cart {self.id} for user {self.user.email}")
                
                # Проверяем доступность товаров и остатки
                for item in cart.items.all():
                    if not item.product.available:
                        logger.error(f"Product {item.product.name} (ID: {item.product.id}) is not available")
                        raise ValidationError(f"Товар {item.product.name} недоступен")
                    
                    if item.product.stock < item.quantity:
                        logger.error(f"Insufficient stock for product {item.product.name} (ID: {item.product.id}): requested {item.quantity}, available {item.product.stock}")
                        raise ValidationError(f"Недостаточно товара {item.product.name} на складе. Запрошено: {item.quantity}, доступно: {item.product.stock}")
                
                logger.info(f"Stock validation passed for cart {self.id}")
                
                # Создаем заказ
                order = Order.objects.create(
                    user=self.user,
                    total_price=self.total_price,
                    address=shipping_address,
                    phone=phone,
                    email=email,
                    comments=comments,
                    status='pending'
                )
                logger.info(f"Created order {order.id} with total_price {self.total_price}")

                # Создаем элементы заказа
                order_items = [
                    OrderItem(
                        order=order,
                        product=item.product,
                        quantity=item.quantity,
                        price=item.product.price
                    ) for item in cart.items.all()
                ]

                OrderItem.objects.bulk_create(order_items)
                logger.info(f"Created {len(order_items)} order items for order {order.id}")

                # Уменьшаем остатки товаров
                for item in cart.items.all():
                    old_stock = item.product.stock
                    item.product.stock -= item.quantity
                    item.product.save()
                    logger.info(f"Updated stock for product {item.product.name} (ID: {item.product.id}): {old_stock} -> {item.product.stock}")

                # Очищаем корзину
                items_count = cart.items.count()
                cart.items.all().delete()
                logger.info(f"Cleared {items_count} items from cart {self.id}")

                logger.info(f"Order creation transaction completed successfully: order_id={order.id}, user={self.user.email}")

        except ValidationError as e:
            logger.error(f"Validation error during order creation for user {self.user.email}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during order creation for user {self.user.email}: {e}", exc_info=True)
            raise

        return order

    def add_product(self, product, quantity=1):
        """
        Добавляет товар в корзину с транзакцией
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            with transaction.atomic():
                logger.info(f"Adding product {product.name} (ID: {product.id}) x{quantity} to cart {self.id} for user {self.user.email}")
                
                # Блокируем корзину для обновления
                cart = Cart.objects.select_for_update().get(id=self.id)
                
                # Проверяем доступность товара
                if not product.available:
                    logger.error(f"Product {product.name} (ID: {product.id}) is not available")
                    raise ValidationError(f"Товар {product.name} недоступен")
                
                # Проверяем остатки
                if product.stock < quantity:
                    logger.error(f"Insufficient stock for product {product.name} (ID: {product.id}): requested {quantity}, available {product.stock}")
                    raise ValidationError(f"Недостаточно товара {product.name} на складе. Запрошено: {quantity}, доступно: {product.stock}")
                
                # Создаем или обновляем элемент корзины
                item, created = CartItem.objects.get_or_create(
                    cart=cart,
                    product=product,
                    defaults={'quantity': quantity}
                )

                if not created:
                    old_quantity = item.quantity
                    item.quantity += quantity
                    item.save()
                    logger.info(f"Updated cart item {item.id}: quantity {old_quantity} -> {item.quantity}")
                else:
                    logger.info(f"Created new cart item {item.id} with quantity {quantity}")
                
                logger.info(f"Successfully added product {product.name} to cart {self.id}")
                return item
                
        except ValidationError as e:
            logger.error(f"Validation error adding product {product.name} to cart {self.id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding product {product.name} to cart {self.id}: {e}", exc_info=True)
            raise

    def clear(self):
        """
        Очистка корзины с транзакцией
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            with transaction.atomic():
                logger.info(f"Starting cart clear transaction for cart {self.id}, user {self.user.email}")
                
                # Блокируем корзину для обновления
                cart = Cart.objects.select_for_update().get(id=self.id)
                
                # Получаем количество элементов для логирования
                items_count = cart.items.count()
                
                if items_count == 0:
                    logger.info(f"Cart {self.id} is already empty")
                    return
                
                # Очищаем корзину
                cart.items.all().delete()
                logger.info(f"Cleared {items_count} items from cart {self.id}")
                
                logger.info(f"Cart clear transaction completed successfully for cart {self.id}")
                
        except Exception as e:
            logger.error(f"Error clearing cart {self.id}: {e}", exc_info=True)
            raise


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
        """
        Сохранение элемента корзины
        """
        # Валидация перед сохранением
        self.full_clean()
        super().save(*args, **kwargs)

class Order(models.Model):
    PROTECTED_FIELDS = ['total_price', 'user']


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._meta.get_field('total_price').editable = False

    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
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

    DELIVERY_METHOD_CHOICES = [
        ('nova_poshta', 'Новая Почта'),
        ('self_pickup', 'Самовывоз'),
        ('other', 'Другое'),
    ]

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
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
    delivery_method = models.CharField(
        max_length=30,
        choices=DELIVERY_METHOD_CHOICES,
        default='other'
    )
    comments = models.TextField(blank=True, null=True, max_length=300)
    nova_poshta_data = models.JSONField(blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['created']),
        ]
        ordering = ('-created',)
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'

    def payment_info(self):
        last_payment = self.payments.filter(status='paid').last()
        if last_payment:
            return {
                "system": last_payment.get_payment_system_display(),
                "amount": last_payment.amount,
                "invoice": last_payment.external_id,
                "details": last_payment.raw_response
            }
        return None

    def can_be_modified(self):
        return self.status in ['pending', 'processing']

    def calculate_total_price(self):
        return sum(
            (item.product.price * item.quantity for item in self.items.all()),
            Decimal('0.00')
        )

    def update_total_price(self):
        """
        Обновление общей стоимости заказа с транзакцией
        """
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            with transaction.atomic():
                logger.info(f"Starting total price update transaction for order {self.id}")
                
                # Блокируем заказ для обновления
                order = Order.objects.select_for_update().get(id=self.id)
                
                old_total = order.total_price
                
                # Пересчитываем стоимость
                total = Decimal(0)
                for item in order.order_items.all():
                    total += item.total_price
                
                order.total_price = total
                order.save()
                
                logger.info(f"Updated order {self.id} total_price: {old_total} -> {total}")
                logger.info(f"Total price update transaction completed successfully for order {self.id}")
                
        except Exception as e:
            logger.error(f"Error updating total price for order {self.id}: {e}", exc_info=True)
            raise

    def clean(self):
        """Валидация заказа"""
        if self.total_price and self.total_price <= 0:
            raise ValidationError("Сумма заказа должна быть положительной")
        super().clean()

    def save(self, *args, **kwargs):
        """
        Сохранение заказа
        """
        # Валидация перед сохранением
        self.full_clean()
        super().save(*args, **kwargs)

    def get_np_weight(self):
        return self.nova_poshta_data.get('weight', '1')

    def get_np_seats(self):
        return self.nova_poshta_data.get('seats', '1')

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

    is_active = models.BooleanField(default=False, verbose_name='Активна')
    _api_key = models.CharField(max_length=255, verbose_name='API ключ (зашифрован)', blank=True)
    _secret_key = models.CharField(max_length=255, verbose_name='Секретный ключ (зашифрован)', blank=True)
    _webhook_secret = models.CharField(max_length=255, blank=True, null=True, verbose_name='Секрет вебхука (зашифрован)')
    is_sandbox = models.BooleanField(default=True, verbose_name='Песочница (sandbox)')

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

    @property
    def sandbox(self):
        return self.is_sandbox

    # Оригинальные значения для сравнения при save
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_api_key = self.api_key
        self.__original_secret_key = self.secret_key
        self.__original_webhook_secret = self.webhook_secret

    def save(self, *args, **kwargs):
        """
        Сохранение настроек платежей
        """
        # Если api_key есть (не пустая строка), и либо _api_key пустое, либо расшифрованное значение отличается — шифруем и записываем
        if self.api_key and (not self._api_key or signing.loads(self._api_key) != self.api_key):
            self._api_key = signing.dumps(self.api_key)

        if self.secret_key and (not self._secret_key or signing.loads(self._secret_key) != self.secret_key):
            self._secret_key = signing.dumps(self.secret_key)

        if self.webhook_secret and (
                not self._webhook_secret or signing.loads(self._webhook_secret) != self.webhook_secret):
            self._webhook_secret = signing.dumps(self.webhook_secret)

        super().save(*args, **kwargs)

        # После сохранения обновляем оригиналы (для последующих сравнений)
        self.__original_api_key = self.api_key
        self.__original_secret_key = self.secret_key
        self.__original_webhook_secret = self.webhook_secret

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Настройка платежей'
        verbose_name_plural = 'Настройки платежей'

    def __str__(self):
        return f"{self.get_payment_system_display()} Settings"


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

    PAYMENT_SYSTEM_CHOICES = [
        ('manual', 'Manual'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('fondy', 'Fondy'),
        ('liqpay', 'LiqPay'),
        ('portmone', 'Portmone'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    external_id = models.CharField(max_length=255, blank=True, null=True)
    raw_response = models.JSONField(blank=True, null=True)
    payment_system = models.CharField(max_length=20, choices=PAYMENT_SYSTEM_CHOICES, default='manual')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        indexes = [
            models.Index(fields=['external_id', 'status']),
        ]

    def get_invoice_info(self):
        return {
            "payment_system": self.get_payment_system_display(),
            "external_id": self.external_id,
            "status": self.status,
            "amount": self.amount,
            "created_at": self.created_at,
            "raw": self.raw_response,
        }

    def __str__(self):
        return f"{self.get_payment_system_display()} | {self.amount} грн | {self.get_status_display()}"



    def save(self, *args, **kwargs):
        """
        Сохранение платежа
        """
        # Автоматически устанавливаем пользователя если не указан
        if not self.user and self.order and self.order.user:
            self.user = self.order.user
        
        super().save(*args, **kwargs)



class NovaPoshtaSettings(models.Model):

    api_key = models.CharField(max_length=255, help_text="API ключ my.novaposhta.ua")
    sender_warehouse_ref = models.CharField(max_length=64, blank=True, verbose_name="Warehouse Ref(ID)",help_text='Ref(ID) отделения отправителя' )
    sender_city_ref = models.CharField(max_length=255, blank=True, null=True, verbose_name='City Ref(ID)', help_text="Ref(ID) города отправителя, например: 8d5a980d-391c-11d...")
    default_sender_name = models.CharField(max_length=255, blank=True, null=True,verbose_name='ФИО отправителя', help_text="ФИО отправителя по умолчанию")
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    default_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, verbose_name='Вес посылки', help_text="Вес одной посылки в кг")
    default_seats_amount = models.PositiveIntegerField(default=1, verbose_name='Количество мест')
    auto_create_ttn = models.BooleanField(default=False, verbose_name="Автоматически создавать ТТН")
    senders_phone = models.CharField(max_length=20, default='0500000000',verbose_name="Телефон отправителя" )


    def __str__(self):
        return "Настройки Новой Почты"



    def save(self, *args, **kwargs):
        """
        Сохранение настроек Новой Почты
        """
        # Проверяем уникальность настроек
        if not self.pk and NovaPoshtaSettings.objects.exists():
            raise ValidationError("Можно создать только одну запись с настройками Новой Почты.")
        
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Nova Poshta Настройка"
        verbose_name_plural = "Nova Poshta Настройки"