# Generated by Django 5.0.9 on 2024-09-05 06:59

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('amount_cents', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
                ('max_purchases', models.IntegerField(validators=[django.core.validators.MinValueValidator(-1)])),
            ],
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notes', models.TextField()),
                ('metadata', models.JSONField()),
                ('method', models.CharField(choices=[('square', 'Square Online Payment'), ('cash', 'In-Person Cash Payment'), ('other', 'Other Payment Method'), ('paypal', 'PayPal Payment (LEGACY - DO NOT USE FOR NEW PAYMENTS)'), ('venmo', 'Venmo Payment (LEGACY - DO NOT USE FOR NEW PAYMENTS)'), ('cashapp', 'Cash App Payment (LEGACY - DO NOT USE FOR NEW PAYMENTS)')], default='other')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('verified_by', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='verified_by', to=settings.AUTH_USER_MODEL)),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='payments.product')),
            ],
        ),
        migrations.CreateModel(
            name='Term',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='payments.product')),
            ],
        ),
    ]