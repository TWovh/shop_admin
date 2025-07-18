from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError



class UserRegistrationForm(UserCreationForm):
    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if len(phone) < 10:
            raise ValidationError("Номер телефона слишком короткий")
        return phone