# Generated by Django 5.1.6 on 2025-03-04 23:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0023_combatrobot_image_url_and_more'),
        ('projects', '0006_team_emoji'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='events', to='projects.project'),
        ),
        migrations.AddField(
            model_name='event',
            name='teams',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='events', to='projects.team'),
        ),
    ]
