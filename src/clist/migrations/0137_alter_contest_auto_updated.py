# Generated by Django 4.2.3 on 2023-12-11 02:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clist', '0136_contest_auto_updated'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contest',
            name='auto_updated',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
