# Generated by Django 3.0.6 on 2020-05-16 17:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0012_remove_session_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='uploadformvars',
            name='session_info',
            field=models.TextField(blank=True, max_length=1000),
        ),
    ]
