"""
Тесты для Django forms
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

from shop.forms import UserRegistrationForm

User = get_user_model()


class UserRegistrationFormTests(TestCase):
    """Тесты для UserRegistrationForm"""
    
    def test_valid_form_data(self):
        """Тест валидных данных формы"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'phone': '+380501234567'
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_phone_too_short(self):
        """Тест невалидного телефона (слишком короткий)"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'phone': '123'  # Слишком короткий
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
        self.assertIn('Номер телефона слишком короткий', str(form.errors['phone']))
    
    def test_valid_phone_minimum_length(self):
        """Тест валидного телефона минимальной длины"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'phone': '1234567890'  # Ровно 10 символов
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_valid_phone_with_plus(self):
        """Тест валидного телефона с плюсом"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'phone': '+380501234567'  # С плюсом
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_valid_phone_with_dashes(self):
        """Тест валидного телефона с дефисами"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'phone': '+380-50-123-45-67'  # С дефисами
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_valid_phone_with_spaces(self):
        """Тест валидного телефона с пробелами"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'phone': '+380 50 123 45 67'  # С пробелами
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_phone_validation_edge_cases(self):
        """Тест граничных случаев валидации телефона"""
        test_cases = [
            ('1234567890', True),      # Ровно 10 символов
            ('123456789', False),      # 9 символов
            ('12345678901', True),     # 11 символов
            ('+1234567890', True),     # 10 символов с плюсом
            ('+123456789', False),     # 9 символов с плюсом
            ('', True),                # Пустая строка (необязательное поле)
            ('abc', False),            # Буквы
            ('123-456-7890', True),    # С дефисами
            ('123 456 7890', True),    # С пробелами
        ]
        
        for phone, should_be_valid in test_cases:
            with self.subTest(phone=phone):
                form_data = {
                    'email': 'test@example.com',
                    'password1': 'testpass123',
                    'password2': 'testpass123',
                    'phone': phone
                }
                
                form = UserRegistrationForm(data=form_data)
                if should_be_valid:
                    self.assertTrue(form.is_valid(), f"Phone {phone} should be valid")
                else:
                    self.assertFalse(form.is_valid(), f"Phone {phone} should be invalid")
                    if phone:  # Не проверяем пустую строку, так как это может быть другая валидация
                        self.assertIn('phone', form.errors)
    
    def test_form_inheritance(self):
        """Тест наследования от UserCreationForm"""
        # Проверяем, что форма наследуется от UserCreationForm
        self.assertTrue(issubclass(UserRegistrationForm, UserCreationForm))
    
    def test_form_fields(self):
        """Тест полей формы"""
        form = UserRegistrationForm()
        
        # Проверяем, что форма содержит необходимые поля
        expected_fields = ['email', 'password1', 'password2', 'phone']
        for field in expected_fields:
            self.assertIn(field, form.fields)
    
    def test_clean_phone_method(self):
        """Тест метода clean_phone"""
        form = UserRegistrationForm()
        
        # Тестируем валидный телефон
        form.cleaned_data = {'phone': '+380501234567'}
        cleaned_phone = form.clean_phone()
        self.assertEqual(cleaned_phone, '+380501234567')
        
        # Тестируем невалидный телефон
        form.cleaned_data = {'phone': '123'}
        with self.assertRaises(ValidationError) as context:
            form.clean_phone()
        
        self.assertIn('Номер телефона слишком короткий', str(context.exception))
    
    def test_form_save_method(self):
        """Тест метода save формы"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'phone': '+380501234567'
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        
        # Сохраняем пользователя
        user = form.save()
        
        # Проверяем, что пользователь создан
        self.assertIsInstance(user, User)
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.phone, '+380501234567')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_form_with_existing_email(self):
        """Тест формы с существующим email"""
        # Создаем пользователя
        User.objects.create_user(
            email='existing@example.com',
            password='testpass123'
        )
        
        # Пытаемся создать пользователя с тем же email
        form_data = {
            'email': 'existing@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'phone': '+380501234567'
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_form_password_mismatch(self):
        """Тест формы с несовпадающими паролями"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'differentpass123',
            'phone': '+380501234567'
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_form_invalid_email(self):
        """Тест формы с невалидным email"""
        form_data = {
            'email': 'invalid-email',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'phone': '+380501234567'
        }
        
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_form_required_fields(self):
        """Тест обязательных полей формы"""
        # Тестируем форму без данных
        form = UserRegistrationForm(data={})
        self.assertFalse(form.is_valid())
        
        # Проверяем, что все обязательные поля имеют ошибки
        required_fields = ['email', 'password1', 'password2']
        for field in required_fields:
            self.assertIn(field, form.errors)
    
    def test_form_phone_field_optional(self):
        """Тест, что поле phone необязательное"""
        form_data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            # phone не указан
        }
        
        form = UserRegistrationForm(data=form_data)
        # Форма должна быть валидной, так как phone необязательное
        self.assertTrue(form.is_valid())