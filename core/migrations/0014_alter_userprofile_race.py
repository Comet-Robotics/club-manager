# Generated by Django 5.1.4 on 2025-02-15 06:23

import multiselectfield.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_alter_userprofile_diet_alter_userprofile_race'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='race',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('W', 'White'), ('B', 'Black or African American'), ('A', 'Asian'), ('N', 'American Indian or Alaska Native'), ('P', 'Native Hawaiian or Other Pacific Islander'), ('M', 'Middle Eastern'), ('O', 'Other')], max_length=13, null=True),
        ),
    ]
