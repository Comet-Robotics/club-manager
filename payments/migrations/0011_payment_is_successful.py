# Generated by Django 5.1.1 on 2024-09-11 20:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0010_alter_payment_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='is_successful',
            field=models.BooleanField(default=False, editable=False),
            preserve_default=False,
        ),
    ]
