# Generated by Django 3.1.2 on 2021-03-24 16:58

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('eveonline', '0014_auto_20210105_1413'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('authentication', '0017_remove_fleetup_permission'),
        ('opcalendar', '0022_auto_20210222_1255'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventVisibility',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Name for the visibility filter', max_length=150)),
                ('ignore_past_fleets', models.BooleanField(default=True, help_text='Should we ignore fleet signals that are in the past')),
                ('color', models.CharField(blank=True, default='', help_text='Color to be displayed on calendar', max_length=7)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this visibility filter is active')),
                ('restricted_to_group', models.ManyToManyField(blank=True, help_text='The group(s) that will be able to see this event visibility type ...', related_name='eventvisibility_require_groups', to='auth.Group')),
                ('restricted_to_state', models.ManyToManyField(blank=True, help_text='The state(s) that will be able to see this event visibility type ...', related_name='eventvisibility_require_states', to='authentication.State')),
            ],
            options={
                'verbose_name': 'Event Visibility Filter',
                'verbose_name_plural': 'Event Visibilities Filters',
            },
        ),
        migrations.AlterModelOptions(
            name='general',
            options={'default_permissions': (), 'managed': False, 'permissions': (('basic_access', 'Can access this app and see operations based on visibility rules'), ('create_event', 'Can create and edit events'), ('manage_event', 'Can delete and manage signups'), ('add_ingame_calendar_owner', 'Can add ingame calendar feeds for their corporation'))},
        ),
        migrations.AddField(
            model_name='event',
            name='external',
            field=models.BooleanField(default=False, help_text='Is the event an external event over API', null=True),
        ),
        migrations.AddField(
            model_name='eventhost',
            name='external',
            field=models.BooleanField(default=False, help_text='External hosts are for NPSI API imports. Checking this box will hide the host in the manual event form.'),
        ),
        migrations.AddField(
            model_name='eventmember',
            name='character',
            field=models.ForeignKey(help_text='Event creator main character', null=True, on_delete=django.db.models.deletion.SET_NULL, to='eveonline.evecharacter'),
        ),
        migrations.AddField(
            model_name='ingameevents',
            name='event_owner_id',
            field=models.IntegerField(null=True),
        ),
        migrations.AddField(
            model_name='ingameevents',
            name='moon_extraction',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AddField(
            model_name='owner',
            name='operation_type',
            field=models.ForeignKey(blank=True, help_text='Event category that will be assigned for all of the events from this owner.', null=True, on_delete=django.db.models.deletion.CASCADE, to='opcalendar.eventcategory'),
        ),
        migrations.AlterField(
            model_name='event',
            name='created_date',
            field=models.DateTimeField(default=django.utils.timezone.now, help_text='When the event was created'),
        ),
        migrations.AlterField(
            model_name='event',
            name='description',
            field=models.TextField(help_text='Description text for the operation'),
        ),
        migrations.AlterField(
            model_name='event',
            name='doctrine',
            field=models.CharField(help_text='Doctrine URL or name', max_length=254),
        ),
        migrations.AlterField(
            model_name='event',
            name='end_time',
            field=models.DateTimeField(help_text='Event end date and time'),
        ),
        migrations.AlterField(
            model_name='event',
            name='eve_character',
            field=models.ForeignKey(help_text='Character used to create the event', null=True, on_delete=django.db.models.deletion.SET_NULL, to='eveonline.evecharacter'),
        ),
        migrations.AlterField(
            model_name='event',
            name='fc',
            field=models.CharField(help_text='Fleet commander/manager for the event', max_length=254),
        ),
        migrations.AlterField(
            model_name='event',
            name='formup_system',
            field=models.CharField(help_text='Location for formup', max_length=254),
        ),
        migrations.AlterField(
            model_name='event',
            name='host',
            field=models.ForeignKey(help_text='Host entity for the event', on_delete=django.db.models.deletion.CASCADE, to='opcalendar.eventhost'),
        ),
        migrations.AlterField(
            model_name='event',
            name='operation_type',
            field=models.ForeignKey(help_text='Event category type', null=True, on_delete=django.db.models.deletion.CASCADE, to='opcalendar.eventcategory'),
        ),
        migrations.AlterField(
            model_name='event',
            name='start_time',
            field=models.DateTimeField(help_text='Event start date and time'),
        ),
        migrations.AlterField(
            model_name='event',
            name='title',
            field=models.CharField(help_text='Title for the event', max_length=200),
        ),
        migrations.AlterField(
            model_name='event',
            name='user',
            field=models.ForeignKey(help_text='User who created the event', on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='eventcategory',
            name='color',
            field=models.CharField(blank=True, default='', help_text='Color to be displayed on calendar', max_length=7),
        ),
        migrations.AlterField(
            model_name='eventcategory',
            name='name',
            field=models.CharField(help_text='Name for the category', max_length=150),
        ),
        migrations.AlterField(
            model_name='eventcategory',
            name='ticker',
            field=models.CharField(help_text='Ticker for the category', max_length=10),
        ),
        migrations.AlterField(
            model_name='eventhost',
            name='ingame_mailing_list',
            field=models.CharField(blank=True, help_text='Ingame mailing list name', max_length=150),
        ),
        migrations.AlterField(
            model_name='eventhost',
            name='logo_url',
            field=models.CharField(blank=True, help_text='Absolute URL for the community logo', max_length=256),
        ),
        migrations.AlterField(
            model_name='webhook',
            name='enabled',
            field=models.BooleanField(default=True, help_text='Is the webhook enabled?'),
        ),
        migrations.AlterField(
            model_name='webhook',
            name='name',
            field=models.CharField(help_text='Name for this webhook', max_length=150),
        ),
        migrations.AlterField(
            model_name='webhook',
            name='webhook_url',
            field=models.CharField(help_text='Webhook URL', max_length=500),
        ),
        migrations.AlterUniqueTogether(
            name='event',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='eventmember',
            unique_together={('event', 'character')},
        ),
        migrations.DeleteModel(
            name='EventSignal',
        ),
        migrations.AddField(
            model_name='eventvisibility',
            name='webhook',
            field=models.ForeignKey(blank=True, help_text='Webhook to send over notifications about these fleet types', null=True, on_delete=django.db.models.deletion.CASCADE, to='opcalendar.webhook'),
        ),
        migrations.RemoveField(
            model_name='event',
            name='visibility',
        ),
        migrations.RemoveField(
            model_name='eventmember',
            name='user',
        ),
        migrations.AddField(
            model_name='event',
            name='event_visibility',
            field=models.ForeignKey(blank=True, help_text='Visibility filter that dictates who is able to see this event', null=True, on_delete=django.db.models.deletion.CASCADE, to='opcalendar.eventvisibility'),
        ),
        migrations.AddField(
            model_name='eventimport',
            name='event_visibility',
            field=models.ForeignKey(help_text='Visibility filter that dictates who is able to see this event', null=True, on_delete=django.db.models.deletion.CASCADE, to='opcalendar.eventvisibility'),
        ),
        migrations.AddField(
            model_name='owner',
            name='event_visibility',
            field=models.ForeignKey(blank=True, help_text='Visibility filter that dictates who is able to see this event', null=True, on_delete=django.db.models.deletion.CASCADE, to='opcalendar.eventvisibility'),
        ),
    ]
