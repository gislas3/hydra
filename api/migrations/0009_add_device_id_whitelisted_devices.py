# Generated by Django 3.2.3 on 2021-11-10 11:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0008_add_batch_updated_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='device_id',
            field=models.UUIDField(default=None, help_text='The id of the device which recorded the device', null=True),
        ),
        migrations.AddField(
            model_name='job_spec',
            name='whitelisted_devices',
            field=models.JSONField(default=list, help_text='The devices (WHICH SHOULD BE A LIST IN JSON FORMAT) that are allowed to trigger this job. Default is an empty list, which means that ALL devices will trigger this job.'),
        ),
    ]
