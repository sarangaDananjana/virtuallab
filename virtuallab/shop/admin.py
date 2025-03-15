from django.contrib import admin
from .models import Game, StorageDevice, FeaturedProducts


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("title", "size", "slug", 'developer',
                    'publisher', 'release_date')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(FeaturedProducts)
class FeaturedProductsAdmin(admin.ModelAdmin):
    list_display = ('title', 'discription', 'button_url')


@admin.register(StorageDevice)
class StorageDeviceAdmin(admin.ModelAdmin):
    list_display = ('category', 'size', 'usable_capacity', 'price')
