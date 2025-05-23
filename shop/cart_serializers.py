from rest_framework import serializers
from .models import CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'total_price']

    def get_total_price(self, obj):
        return obj.total_price


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(default=1)