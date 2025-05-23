from rest_framework import serializers
from .models import Product, Category, Order, OrderItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class ProductSerializer(serializers.ModelSerializer):
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть положительной.")
        return value

    def validate(self, data):
        if not data['available'] and 'price' in data:
            raise serializers.ValidationError("Нельзя менять цену недоступного товара")
        return data

    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'category',
                  'image', 'description', 'price',
                  'available', 'created', 'updated']


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
    quantity = serializers.IntegerField(min_value=1, max_value=100)

