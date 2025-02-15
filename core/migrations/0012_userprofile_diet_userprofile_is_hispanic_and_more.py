# Generated by Django 5.1.4 on 2025-02-15 05:07

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_alter_userprofile_is_utd_affiliate'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='diet',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('S', 'Shellfish Allergy'), ('N', 'Nut Allergy'), ('VT', 'Vegetarian'), ('VN', 'Vegan'), ('P', 'Pescatarian'), ('H', 'Halal'), ('K', 'Kosher'), ('L', 'Lactose Intolerant'), ('G', 'Gluten Free')], default=None, max_length=2), blank=True, default=None, null=True, size=None),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='is_hispanic',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='is_lgbt',
            field=models.BooleanField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='race',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('W', 'White'), ('B', 'Black or African American'), ('A', 'Asian'), ('N', 'American Indian or Alaska Native'), ('P', 'Native Hawaiian or Other Pacific Islander')], default=None, max_length=1), blank=True, default=None, null=True, size=None),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='shirt',
            field=models.CharField(blank=True, choices=[('XS', 'XS'), ('S', 'Small'), ('M', 'Medium'), ('L', 'Large'), ('XL', 'XL'), ('XXL', '2XL'), ('XXXL', '3XL')], max_length=4, null=True),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='gender',
            field=models.CharField(blank=True, choices=[('M', 'Man'), ('F', 'Woman'), ('N', 'Non-Binary'), ('O', 'Other')], max_length=1, null=True),
        ),
    ]
