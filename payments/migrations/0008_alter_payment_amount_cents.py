# Generated by Django 5.0.9 on 2024-09-08 22:51

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0007_payment_amount_cents_alter_payment_method'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='amount_cents',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(0)]),
        ),
    ]