# Generated by Django 5.1.2 on 2024-10-17 09:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0005_event_url'),
        ('payments', '0018_alter_payment_created_at_alter_payment_updated_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='CombatEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('documenso_minor_waiver_id', models.CharField()),
                ('documenso_adult_waiver_id', models.CharField()),
                ('robot_combat_events_event_id', models.CharField()),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='public_events', to='events.event')),
                ('product_id', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='payments.product')),
            ],
        ),
        migrations.CreateModel(
            name='CombatEventRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('robot_combat_events_robot_id', models.CharField()),
                ('combat_event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='events.combatevent')),
            ],
        ),
    ]
