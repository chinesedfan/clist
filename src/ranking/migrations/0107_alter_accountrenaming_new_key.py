# Generated by Django 4.2.3 on 2023-12-10 15:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ranking', '0106_alter_accountrenaming_new_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accountrenaming',
            name='new_key',
            field=models.CharField(blank=True, max_length=1024, null=True),
        ),
    ]
