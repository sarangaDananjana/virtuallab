from django.db import models
from tinymce.models import HTMLField


class Game(models.Model):
    title = models.CharField(max_length=255)
    preview_image = models.ImageField(
        upload_to='images/game_images/', blank=True)
    big_preview_image = models.ImageField(
        upload_to='images/game_images/', blank=True)
    game_edition = models.CharField(max_length=255, default=1)
    size = models.IntegerField()
    logo = models.ImageField(
        upload_to='images/games/logo', default='fallback.png', blank=True)
    discription = HTMLField()
    slug = models.SlugField(unique=True)
    developer = models.CharField(max_length=255)
    publisher = models.CharField(max_length=255)
    release_date = models.DateField()
    minimum_os = models.CharField(max_length=255)
    minimum_processor = models.CharField(max_length=255)
    minimum_memory = models.CharField(max_length=255)
    minimum_storage = models.CharField(max_length=255)
    minimum_graphics = models.CharField(max_length=255)
    minimum_other = models.CharField(max_length=255, null=True)
    maximum_os = models.CharField(max_length=255)
    maximum_processor = models.CharField(max_length=255)
    maximum_memory = models.CharField(max_length=255)
    maximum_storage = models.CharField(max_length=255)
    maximum_graphics = models.CharField(max_length=255)
    maximum_other = models.CharField(max_length=255, null=True)
    image_1 = models.ImageField(
        upload_to='images/game_images/', blank=True)
    image_2 = models.ImageField(
        upload_to='images/game_images/', blank=True)
    image_3 = models.ImageField(
        upload_to='images/game_images/', blank=True)
    image_4 = models.ImageField(
        upload_to='images/game_images/', blank=True)
    image_5 = models.ImageField(
        upload_to='images/game_images/', blank=True)
    image_6 = models.ImageField(
        upload_to='images/game_images/', blank=True)
    video = models.FileField(
        upload_to='images/game_videos/', blank=True)


class StorageDevice(models.Model):
    category = models.CharField(max_length=255, blank=True)
    size = models.CharField(max_length=255)
    usable_capacity = models.PositiveIntegerField()
    price = models.PositiveIntegerField()
    image = models.ImageField(upload_to='images/hard_images/', blank=True)
    discription = models.CharField(max_length=1000, blank=True)


class FeaturedProducts(models.Model):
    logo = models.ImageField(
        upload_to='images/featured_product/logos/', default='fallback.png', blank=True)
    mobile_cover_image = models.ImageField(
        upload_to='images/featured_product/main_image', default='fallback.png', blank=True)
    title = models.CharField(max_length=255)
    discription = models.CharField(max_length=511, default=0)
    button_url = models.CharField(max_length=1500)
    desktop_cover_image = models.ImageField(
        upload_to='images/featured_product/main_image', default='fallback.png', blank=True)
