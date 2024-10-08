# Generated by Django 5.1.1 on 2024-09-12 03:36

import common.utils
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0011_payment_is_successful'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='verified_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='verified_by', to=settings.AUTH_USER_MODEL, validators=[common.utils.validate_staff]),
        ),
    ]
