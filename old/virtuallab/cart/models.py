from django.db import models
from django.contrib.auth.models import User
from shop.models import StorageDevice, Game


class Cart(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    cart_price = models.PositiveIntegerField()
    cart_storage = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cart_game = models.ManyToManyField(Game)
    cart_storage_name = models.CharField(max_length=255, blank=True)
    cart_storage_category = models.CharField(max_length=255, blank=True)


class Order(models.Model):
    PENDING_PAYMENT = 'P'
    PAYMENT_IDENTIFIED = 'I'
    PAYMENT_COMPLETE = 'C'
    PAYEMENT_FAILED = 'F'
    PAYMENT_STATUS_CHOICES = [
        (PENDING_PAYMENT, 'Pending'),
        (PAYMENT_IDENTIFIED, 'Identified'),
        (PAYMENT_COMPLETE, 'Complete'),
        (PAYEMENT_FAILED, 'Failed')
    ]
    user = models.ForeignKey(User, on_delete=models.PROTECT, default=1)
    order_created_at = models.DateTimeField(auto_now_add=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    e_mail = models.EmailField()
    phone_number = models.CharField(
        max_length=10, help_text='0771234567')
    address = models.CharField(max_length=1000, default=0)
    game_list = models.ManyToManyField(Game)
    orderd_storage = models.PositiveIntegerField(null=True)
    order_value = models.PositiveBigIntegerField(null=True)
    order_status = models.CharField(
        max_length=1, choices=PAYMENT_STATUS_CHOICES, default=PENDING_PAYMENT)
    payment_proof = models.ImageField(
        upload_to='payment_slips/')
