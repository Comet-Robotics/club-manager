# Generated by Django 5.1.6 on 2025-02-18 22:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_serversettings_photo_alter_userprofile_major'),
    ]

    operations = [
        migrations.RenameField(
            model_name='serversettings',
            old_name='photo',
            new_name='logo',
        ),
    ]
