# Generated by Django 5.1.1 on 2024-09-10 06:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_userprofile_discord_id_alter_userprofile_gender'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='discord_id',
            field=models.CharField(blank=True, choices=[('discord', 'Discord'), ('other', 'Other')], max_length=200),
        ),
    ]