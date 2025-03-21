# Generated by Django 5.1.3 on 2024-12-20 16:01

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('shop', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cart_price', models.PositiveIntegerField()),
                ('cart_storage', models.PositiveIntegerField()),
                ('cart_storage_name', models.CharField(blank=True, max_length=255)),
                ('cart_storage_category', models.CharField(blank=True, max_length=255)),
                ('cart_game', models.ManyToManyField(to='shop.game')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_created_at', models.DateTimeField(auto_now_add=True)),
                ('first_name', models.CharField(max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('e_mail', models.EmailField(max_length=254)),
                ('phone_number', models.CharField(help_text='0771234567', max_length=10)),
                ('address', models.CharField(default=0, max_length=1000)),
                ('orderd_storage', models.PositiveIntegerField(null=True)),
                ('order_value', models.PositiveBigIntegerField(null=True)),
                ('order_status', models.CharField(choices=[('P', 'Pending'), ('I', 'Identified'), ('C', 'Complete'), ('F', 'Failed')], default='P', max_length=1)),
                ('payment_proof', models.ImageField(upload_to='payment_slips/')),
                ('game_list', models.ManyToManyField(to='shop.game')),
                ('user', models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
