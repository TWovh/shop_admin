from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from django.forms import ValidationError
from django.contrib.auth import get_user_model
from decimal import Decimal
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from django.test import TestCase
from shop.models import Product, Category

User = get_user_model()

class SecurityTests(APITestCase):
    def test_admin_access(self):
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)  # редирект на логин


class ProductModelTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Electronics", slug="electronics")
        self.product = Product.objects.create(
            category=self.category,
            name="Test Product",
            slug="test-product",
            price=Decimal("19.99"),
            stock=5
        )

    def test_product_str(self):
        self.assertEqual(str(self.product), "Test Product")

    def test_get_absolute_url(self):
        url = self.product.get_absolute_url()
        expected = reverse('shop:product_detail', args=[self.product.id, self.product.slug])
        self.assertEqual(url, expected)

    def test_clean_negative_price(self):
        self.product.price = -1
        with self.assertRaises(ValidationError):
            self.product.clean()

    def test_image_preview_with_image(self):
        self.product.image = "products/2025/05/27/test.jpg"
        html = self.product.image_preview()
        self.assertIn('<img', html)
        self.assertIn('width="150"', html)

    def test_image_preview_without_image(self):
        self.product.image = ""
        self.assertEqual(self.product.image_preview(), "Нет изображения")


class ProductAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin',
                                             email='admin@example.com',
                                             password='admin123')
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)

        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        self.category = Category.objects.create(name="Books", slug="books")

    def test_create_product_authenticated(self):
        url = reverse('product-list')
        data = {
            "category": self.category.id,
            "name": "API Product",
            "slug": "api-product",
            "price": "12.50",
            "stock": 20
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 1)

    def test_create_product_invalid_price(self):
        url = reverse('product-list')
        data = {
            "category": self.category.id,
            "name": "Invalid Product",
            "slug": "invalid-product",
            "price": "-10.00",
            "stock": 5
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_product(self):
        product = Product.objects.create(
            category=self.category,
            name="Old Name",
            slug="old-name",
            price=20.00,
            stock=2
        )
        url = reverse('shop:product-detail', args=[product.id, product.slug])
        data = {
            "category": self.category.id,
            "name": "Updated Name",
            "slug": "updated-name",
            "price": "25.00",
            "stock": 10
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        product.refresh_from_db()
        self.assertEqual(product.name, "Updated Name")
        self.assertEqual(product.price, Decimal("25.00"))

    def test_list_products(self):
        Product.objects.create(
            category=self.category,
            name="Book 1",
            slug="book-1",
            price=5.00,
            stock=2
        )
        Product.objects.create(
            category=self.category,
            name="Book 2",
            slug="book-2",
            price=10.00,
            stock=5
        )
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

class ProductModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Books', slug='books')
        self.product = Product.objects.create(
            name='Test Book',
            slug='test-book',
            category=self.category,
            price=15.99,
            stock=3,
            available=True
        )

    def test_get_absolute_url(self):
        url = self.product.get_absolute_url()
        self.assertIn(str(self.product.slug), url)


class ProductAPITestGet(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Tech', slug='tech')
        self.product = Product.objects.create(
            name='Laptop',
            slug='laptop',
            category=self.category,
            price=999.99,
            stock=10,
            available=True
        )

    def test_get_product_detail(self):
        url = reverse('shop:product-detail', args=[self.product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Laptop')