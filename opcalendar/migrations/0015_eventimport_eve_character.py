# Generated by Django 3.1.2 on 2021-01-13 09:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('eveonline', '0012_index_additions'),
        ('opcalendar', '0014_auto_20210113_0836'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventimport',
            name='eve_character',
            field=models.ForeignKey(help_text='Event creator main character', null=True, on_delete=django.db.models.deletion.SET_NULL, to='eveonline.evecharacter'),
        ),
    ]
