# Generated by Django 5.1.1 on 2024-09-10 22:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0009_rename_max_purchases_product_max_purchases_per_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='notes',
            field=models.TextField(blank=True, null=True),
        ),
    ]