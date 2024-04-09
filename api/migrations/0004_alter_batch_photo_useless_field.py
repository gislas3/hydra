# Generated by Django 3.2.3 on 2021-08-11 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_batch_photo_useless_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='batch_photo',
            name='useless_field',
            field=models.BooleanField(default=True, help_text=('This field is only being added as serialized models ', 'need a field so they can accept data. Please refactor')),
        ),
    ]
