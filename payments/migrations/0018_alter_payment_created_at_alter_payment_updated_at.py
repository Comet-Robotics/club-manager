# Generated by Django 5.1.1 on 2024-09-16 20:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0017_alter_payment_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='payment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
