# Generated by Django 3.1.2 on 2021-03-14 12:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("opcalendar", "0026_auto_20210314_1046"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventvisibility",
            name="color",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Color to be displayed on calendar",
                max_length=7,
            ),
        ),
    ]