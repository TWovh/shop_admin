# Generated by Django 5.2.1 on 2025-07-05 17:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0011_remove_product_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="productimage",
            name="is_main",
            field=models.BooleanField(default=False, verbose_name="Главная картинка"),
        ),
    ]
