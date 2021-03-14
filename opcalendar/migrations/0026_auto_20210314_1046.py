# Generated by Django 3.1.2 on 2021-03-14 10:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('opcalendar', '0025_auto_20210314_1043'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventvisibility',
            name='webhook',
            field=models.ForeignKey(blank=True, help_text='Webhook to send over notifications about these fleet types', null=True, on_delete=django.db.models.deletion.CASCADE, to='opcalendar.webhook'),
        ),
    ]
