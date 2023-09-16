# Generated by Django 4.2.3 on 2023-09-10 21:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clist', '0113_resource_last_rating_update_time'),
    ]

    operations = [
        migrations.RenameField(
            model_name='resource',
            old_name='last_rating_update_time',
            new_name='rank_update_time',
        ),
        migrations.AddField(
            model_name='resource',
            name='rating_update_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
