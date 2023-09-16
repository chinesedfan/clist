# Generated by Django 4.2.3 on 2023-09-16 10:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ranking', '0090_remove_account_country_rank_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='account',
            name='ranking_acc_resourc_65aa35_idx',
        ),
        migrations.RemoveIndex(
            model_name='account',
            name='ranking_acc_resourc_023f63_idx',
        ),
        migrations.RenameField(
            model_name='account',
            old_name='rank',
            new_name='overall_rank',
        ),
        migrations.AddIndex(
            model_name='account',
            index=models.Index(fields=['resource', 'overall_rank'], name='ranking_acc_resourc_3e0b3f_idx'),
        ),
        migrations.AddIndex(
            model_name='account',
            index=models.Index(fields=['resource', '-overall_rank'], name='ranking_acc_resourc_6512c4_idx'),
        ),
    ]
