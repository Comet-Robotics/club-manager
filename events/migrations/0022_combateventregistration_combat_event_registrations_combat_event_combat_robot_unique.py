# Generated by Django 5.1.2 on 2024-11-13 07:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0021_combateventregistration_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='combateventregistration',
            constraint=models.UniqueConstraint(fields=('combat_event', 'combat_robot'), name='combat_event_registrations_combat_event_combat_robot_unique'),
        ),
    ]
