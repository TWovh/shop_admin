from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('email', 'password1', 'password2', 'phone')
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone:
            # Убираем все символы кроме цифр для подсчета длины
            digits_only = ''.join(filter(str.isdigit, phone))
            if len(digits_only) < 10:
                raise ValidationError("Номер телефона слишком короткий")
        return phone