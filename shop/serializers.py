from rest_framework import serializers
from .models import Product, Category, Order, OrderItem, CartItem
from rest_framework.serializers import Serializer
from rest_framework.reverse import reverse
from rest_framework.exceptions import ValidationError
from rest_framework.serializers import CharField, EmailField, ChoiceField

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'category',
            'image', 'description', 'price',
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
        if not data['available'] and 'price' in data:
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


