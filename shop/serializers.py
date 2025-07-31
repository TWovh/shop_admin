from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Product, Category, Order, OrderItem, CartItem, ProductImage, PaymentSettings, Payment
from rest_framework.serializers import Serializer
from rest_framework.reverse import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import CharField, EmailField, ChoiceField

User = get_user_model()

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ['image', 'alt_text', 'is_main']

    def get_image(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url) if obj.image and request else None

class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    images = ProductImageSerializer(many=True, read_only=True)
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'category',
            'images', 'main_image', 'description', 'price',
            'available', 'created', 'updated',
        ]

    def get_main_image(self, obj):
        request = self.context.get('request')
        main_img = obj.images.filter(is_main=True).first()
        if main_img and main_img.image:
            return request.build_absolute_uri(main_img.image.url)
        return None

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть положительной.")
        return value

    def validate(self, data):
        if not data.get('available', True) and 'price' in data:
            raise serializers.ValidationError("Нельзя менять цену недоступного товара")
        return data


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity', 'price', 'total_price']
        read_only_fields = ['price', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'status', 'total_price', 'address',
                  'phone', 'email', 'comments', 'created', 'items']
        read_only_fields = ['user', 'status', 'total_price', 'created', 'items']

    def validate_phone(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Номер телефона слишком короткий")
        return value


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, max_value=100)

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price']

    def get_total_price(self, obj):
        return obj.product.price * obj.quantity

class OrderCreateSerializer(serializers.Serializer):
    address = serializers.CharField(required=True)
    phone = serializers.CharField(required=True)
    email = serializers.EmailField(required=True)
    city = serializers.CharField(required=True)
    delivery_type = serializers.ChoiceField(choices=[('prepaid', 'Оплата онлайн'), ('cod', 'Наложенный платеж')],
                                            default='prepaid')
    comments = serializers.CharField(required=False, allow_blank=True, default='')


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'role']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    phone = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'phone')

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            phone=validated_data.get('phone', ''),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'phone', 'role')


class PaymentSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentSettings
        fields = ['payment_system', 'is_active']


class PaymentMethodSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()

    class Meta:
        model = PaymentSettings
        fields = ['payment_system', 'is_active', 'is_sandbox', 'title']

    def get_title(self, obj):
        return obj.get_payment_system_display()

class PaymentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_system', 'external_id', 'status',
            'amount', 'created_at', 'raw_response'
        ]



class DashboardOverviewSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField(allow_blank=True)
    active_orders_count = serializers.SerializerMethodField()
    last_order = serializers.SerializerMethodField()

    def get_active_orders_count(self, user):
        return user.orders.filter(status='processing').count()

    def get_last_order(self, user):
        last = user.orders.order_by('-created').first()
        if last:
            return {
                'id': last.id,
                'created_at': last.created_at,
                'total_price': str(last.total_price),
                'payment_status': last.payment_status,
                'status': last.status,
            }
        return None


class DashboardProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'phone']

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Email уже используется другим пользователем.")
        return value


class DashboardOrderListSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()
    created = serializers.DateTimeField(format="%d.%m.%Y %H:%M")
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Order
        fields = [
            'id', 'created', 'status', 'payment_status',
            'total_price', 'delivery_type', 'item_count'
        ]

    def get_item_count(self, obj):
        return obj.order_items.count()

class DashboardOrderDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    delivery_info = serializers.SerializerMethodField()
    payment_info = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'created', 'total_price',
            'payment_status', 'status',
            'address', 'delivery_info', 'payment_info', 'items'
        ]

    def get_items(self, obj):
        items = []
        for item in obj.order_items.all():
            product = item.product
            main_image = product.images.filter(is_main=True).first()
            image_url = main_image.image.url if main_image and main_image.image else None

            items.append({
                'product_name': product.name,
                'quantity': item.quantity,
                'price': str(item.price),
                'total': str(item.total_price),
                'image': image_url,
            })
        return items
    def get_delivery_info(self, obj):
        from .models import NovaPoshtaSettings

        if NovaPoshtaSettings.objects.filter(is_active=True).exists() and obj.nova_poshta_data:
            return {
                'ttn': obj.nova_poshta_data.get('ttn'),
                'status': obj.nova_poshta_data.get('status'),
                'city': obj.nova_poshta_data.get('city'),
                'warehouse': obj.nova_poshta_data.get('warehouse')
            }
        else:
            return {
                'status': 'Обрабатывается' if obj.status == 'processing' else 'Не отправлен'
            }

    def get_payment_info(self, obj):
        return obj.payment_info()

class DashboardOrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.main_image', read_only=True)
    product_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'product_image', 'product_price', 'quantity', 'total_price']
