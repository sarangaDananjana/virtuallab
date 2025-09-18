from .models import Ticket, TicketPhoto  # add these to your existing imports
from django.utils.html import format_html
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from .models import (
    Genre,
    Company,
    Product,
    ProductImage,
    SystemRequirements,
    Cart,
    CartItem,
    Order,
    OrderItem,
    ReservedSlot,
    GameRequest,
    DLC,
    StorageDevice,
    OrderStorageItem, Blog, BlogPhoto
)
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AlreadyRegistered
from decimal import Decimal
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Extra", {"fields": ("phone_number",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (None, {"fields": ("phone_number",)}),
    )
    list_display = ("id", "username", "email",
                    "phone_number", "is_staff", "customer_id", "is_cod_approved")
    search_fields = ("username", "email", "phone_number")


# -- Optional: register the custom User in admin (if not already registered)
User = get_user_model()
try:
    admin.site.register(User, BaseUserAdmin)
except AlreadyRegistered:
    pass


# =========================
# Inline configurations
# =========================
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    readonly_fields = ("preview",)

    def preview(self, obj):
        if getattr(obj, "image", None):
            return f"<img src='{obj.image.url}' style='height:60px' />"
        return ""

    preview.allow_tags = True
    preview.short_description = "Preview"


class SystemRequirementsInline(admin.StackedInline):
    model = SystemRequirements
    extra = 0
    can_delete = False


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    autocomplete_fields = ["product"]
    readonly_fields = ("subtotal",)

    def subtotal(self, obj):
        if not obj.pk:
            return "—"
        total = (obj.unit_price or Decimal("0")) * (obj.quantity or 0)
        return f"{total}"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ["product"]
    readonly_fields = ("subtotal",)

    def subtotal(self, obj):
        if not obj.pk:
            return "—"
        total = (obj.unit_price or Decimal("0")) * (obj.quantity or 0)
        return f"{total}"


# =========================
# Model admins
# =========================
@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "company_type", "website")
    list_filter = ("company_type",)
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(DLC)
class DLCAdmin(admin.ModelAdmin):
    list_display = ("product", "title", "description", "image")
    list_filter = ("product",)
    search_fields = ("title",)
    ordering = ("product",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductImageInline, SystemRequirementsInline]

    list_display = (
        "title",
        "edition",
        "sku",
        "price",
        "currency",
        "is_active",
        "developer",
        "publisher",
        "game_size_gb",
        "image_count",
        "created_at",
    )
    list_filter = ("is_active", "developer", "publisher", "genres")
    search_fields = ("title", "sku", "description")
    list_select_related = ("developer", "publisher")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["developer", "publisher", "genres"]
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"

    @admin.display(description="Images", ordering=None)
    def image_count(self, obj):
        return obj.images.count()

    actions = [
        "activate_products",
        "deactivate_products",
    ]

    @admin.action(description="Mark selected products as active")
    def activate_products(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} product(s).")

    @admin.action(description="Mark selected products as inactive")
    def deactivate_products(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} product(s).")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemInline]
    list_display = ("id", "users_display", "session_key",
                    "total_display", "created_at", "updated_at")
    search_fields = ("session_key", "users__username", "users__email")
    autocomplete_fields = ["users"]
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"

    def users_display(self, obj):
        users = obj.users.all()[:3]
        label = ", ".join(u.username for u in users)
        extra = obj.users.count() - len(users)
        return f"{label}{' +' + str(extra) if extra > 0 else ''}" or "—"

    users_display.short_description = "Users"

    def total_display(self, obj):
        return obj.total

    total_display.short_description = "Total"


class OrderStorageItemInline(admin.TabularInline):
    model = OrderStorageItem
    extra = 0
    autocomplete_fields = ["product"]
    readonly_fields = ("subtotal",)

    def subtotal(self, obj):
        if not obj.pk:
            return "—"
        total = (obj.unit_price or Decimal("0")) * (obj.quantity or 0)
        return f"{total}"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # show BOTH kinds of order lines inline
    inlines = [OrderItemInline, OrderStorageItemInline]

    list_display = (
        "id",
        "status",
        "payment_method",
        "currency",
        # stored checkout total (may include device)
        "order_value",
        # computed: direct + storage items (excl. device)
        "items_only_total_display",
        "direct_count",
        "storage_count",
        "storage_device_price", "storage_device_name",
        "ordered_at",
        "users_display",
    )
    list_filter = ("status", "payment_method")
    search_fields = (
        "id",
        "users__username",
        "users__email",
        "orderitem__product__title",
        "orderitem__product__sku",
        # ⬇️ now searchable by storage items too
        "storage_items__product__title",
        "storage_items__product__sku",
        "payment_reference",
    )
    autocomplete_fields = ["users"]
    readonly_fields = ("ordered_at", "created_at", "updated_at", "items_only_total_display",
                       "direct_count", "storage_count")

    fieldsets = (
        (None, {"fields": (
            "users", "guest_email", "status",
            "payment_method", "payment_reference",
            "currency", "order_value",
            "storage_device_name", "storage_device_price",
            "notes",
        )}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
    date_hierarchy = "ordered_at"

    # ---- helpful computed displays ----
    @admin.display(description="Direct items")
    def direct_count(self, obj):
        return obj.orderitem_set.count()

    @admin.display(description="Storage items")
    def storage_count(self, obj):
        # OrderStorageItem uses related_name="storage_items" in your models
        return obj.storage_items.count()

    @admin.display(description="Items-only total")
    def items_only_total_display(self, obj):
        # Sum of direct + storage items (EXCLUDES any device price)
        total_direct = sum(
            (it.unit_price or Decimal("0")) * (it.quantity or 0)
            for it in obj.orderitem_set.all()
        )
        total_storage = sum(
            (si.unit_price or Decimal("0")) * (si.quantity or 0)
            for si in obj.storage_items.all()
        )
        return total_direct + total_storage

    def users_display(self, obj):
        users = obj.users.all()[:3]
        label = ", ".join(u.username for u in users)
        extra = obj.users.count() - len(users)
        return f"{label}{' +' + str(extra) if extra > 0 else ''}" or "—"
    users_display.short_description = "Users"


class TicketPhotoInlineFormSet(BaseInlineFormSet):
    """Limit a ticket to max 5 photos."""

    def clean(self):
        super().clean()
        count = 0
        for form in self.forms:
            if not form.cleaned_data:
                continue
            if form.cleaned_data.get("DELETE", False):
                continue
            # Count existing or newly uploaded photos
            if form.instance.pk or form.cleaned_data.get("image"):
                count += 1
        if count > 5:
            raise ValidationError("You can upload up to 5 photos per ticket.")


class TicketPhotoInline(admin.TabularInline):
    model = TicketPhoto
    formset = TicketPhotoInlineFormSet
    extra = 0
    max_num = 5
    fields = ("image", "alt_text")
    show_change_link = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    inlines = [TicketPhotoInline]

    list_display = (
        "reference",
        "subject",
        "source",
        "status",
        "priority",
        "order",
        "photos_total",
        "video_attached",
        "created_at",
        "updated_at",
        "users_display",
    )
    list_filter = ("source", "status", "priority", "created_at")
    search_fields = ("reference", "subject", "description",
                     "order__id", "users__username", "users__email")
    autocomplete_fields = ("users", "order")
    readonly_fields = ("reference", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("reference", "subject", "description", "source", "order")}),
        ("Attachments", {"fields": ("video",)}),
        ("Workflow", {"fields": ("status", "priority", "users")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(boolean=True, description="Video")
    def video_attached(self, obj):
        return bool(obj.video)

    @admin.display(description="Photos")
    def photos_total(self, obj):
        return obj.photos.count()

    def users_display(self, obj):
        users = obj.users.all()[:3]
        label = ", ".join(u.username for u in users)
        extra = obj.users.count() - len(users)
        return f"{label}{' +' + str(extra) if extra > 0 else ''}" or "—"


@admin.register(ReservedSlot)
class ReservedSlotAdmin(admin.ModelAdmin):
    list_display = ("date", "slot", "user", "ticket", "created_at")
    list_filter = ("slot", "date", "created_at")
    search_fields = (
        "ticket__reference", "ticket__subject",
        "user__username", "user__email",
    )
    list_select_related = ("user", "ticket")
    autocomplete_fields = ("user", "ticket")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("ticket", "user")}),
        ("Reservation", {"fields": ("date", "slot", "notes")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(GameRequest)
class GameRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "game_name", "edition_name", "user", "request_date")
    list_filter = ("request_date",)
    search_fields = ("game_name", "edition_name",
                     "user__username", "user__email")
    autocomplete_fields = ("user",)
    ordering = ("-request_date",)


@admin.register(StorageDevice)
class StorageDeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "true_capacity_gb",
                    "marketing_capacity_gb")
    list_filter = ("category",)
    search_fields = ("name",)


class BlogPhotoInline(admin.TabularInline):
    model = BlogPhoto
    extra = 0
    fields = ("image", "alt_text", "order", "preview")
    readonly_fields = ("preview",)
    ordering = ("order", "id")

    def preview(self, obj):
        if getattr(obj, "image", None):
            # Small thumbnail preview
            return format_html(
                "<img src='{}' style='height:70px;border-radius:6px'/>",
                obj.image.url,
            )
        return "—"

    preview.short_description = "Preview"

# 3) Blog admin with cover preview and handy actions


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    inlines = [BlogPhotoInline]

    list_display = (
        "title",
        "category",
        "is_featured",
        "reading_time_minutes",
        "created_at",
        "cover_preview",
    )
    list_filter = ("category", "is_featured", "created_at")
    search_fields = ("title", "content_en", "content_si")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "cover_preview")
    fields = (
        "title",
        "slug",
        "category",
        "is_featured",
        "reading_time_minutes",
        "main_image",
        "cover_preview",
        "content_en",
        "content_si",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def cover_preview(self, obj):
        if getattr(obj, "main_image", None):
            return format_html(
                "<img src='{}' style='height:120px;border-radius:8px'/>",
                obj.main_image.url,
            )
        return "—"

    cover_preview.short_description = "Main image"

    # Quick feature/unfeature actions
    actions = ["mark_featured", "unmark_featured"]

    @admin.action(description="Mark selected posts as FEATURED")
    def mark_featured(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f"Featured {updated} post(s).")

    @admin.action(description="Unmark selected posts as featured")
    def unmark_featured(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f"Unfeatured {updated} post(s).")

# 4) (Optional) Standalone admin for BlogPhoto for quick searching


@admin.register(BlogPhoto)
class BlogPhotoAdmin(admin.ModelAdmin):
    list_display = ("blog", "order", "image_preview", "alt_text")
    list_filter = ("blog__category",)
    search_fields = ("blog__title", "alt_text")
    autocomplete_fields = ("blog",)
    ordering = ("blog__created_at", "order", "id")

    def image_preview(self, obj):
        if getattr(obj, "image", None):
            return format_html(
                "<img src='{}' style='height:50px;border-radius:5px'/>",
                obj.image.url,
            )
        return "—"

    image_preview.short_description = "Preview"
