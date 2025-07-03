from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from .models import Product, Category, Order, OrderItem, CartItem, ProductImage
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
        fields = ['image', 'alt_text']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.image.url

class ProductSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    category = serializers.StringRelatedField()
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'category',
            'images', 'description', 'price',
            'available', 'created', 'updated',
            'url',
        ]

    def get_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.get_absolute_url())

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
        fields = ['id', 'user', 'status', 'total_price', 'shipping_address',
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
    product = ProductSerializer(read_only=True)  # Вложенный сериализатор продукта
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price']

    def get_total_price(self, obj):
        return obj.product.price * obj.quantity

class CreateOrderSerializer(serializers.Serializer):
    address = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.EmailField()
    city = serializers.CharField()
    delivery_type = serializers.ChoiceField(choices=[('prepaid', 'Оплата онлайн'), ('cod', 'Наложенный платеж')], default='prepaid')
    comments = serializers.CharField(required=False, allow_blank=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'phone', 'role']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'phone', 'password', 'password2']  # username убираем, используем email

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user