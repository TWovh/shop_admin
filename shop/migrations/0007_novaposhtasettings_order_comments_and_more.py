# Generated by Django 5.2.1 on 2025-06-30 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shop", "0006_alter_order_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="NovaPoshtaSettings",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "api_key",
                    models.CharField(
                        help_text="API ключ my.novaposhta.ua", max_length=255
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Nova Poshta Настройка",
                "verbose_name_plural": "Nova Poshta Настройки",
            },
        ),
        migrations.AddField(
            model_name="order",
            name="comments",
            field=models.TextField(blank=True, max_length=300, null=True),
        ),
        migrations.AlterField(
            model_name="paymentsettings",
            name="payment_system",
            field=models.CharField(
                choices=[
                    ("stripe", "Stripe"),
                    ("paypal", "PayPal"),
                    ("portmone", "Portmone"),
                    ("liqpay", "LiqPay"),
                    ("fondy", "Fondy"),
                ],
                default="stripe",
                max_length=20,
                verbose_name="Платежная система",
            ),
        ),
    ]
