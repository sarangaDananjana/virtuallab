# Generated by Django 5.1.3 on 2024-12-30 12:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0004_game_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='views',
            field=models.IntegerField(default=0),
        ),
    ]
