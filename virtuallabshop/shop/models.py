from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from uuid import uuid4
from django.utils.text import slugify
from django.core.validators import RegexValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from decimal import Decimal
import uuid
import os

# SKU generator (callable is required because Django can't serialize lambdas in migrations)


def generate_sku():
    return uuid.uuid4().hex[:12].upper()


def generate_ticket_ref():
    return "TCK-" + uuid.uuid4().hex[:8].upper()


# --- Existing custom user ----------------------------------------------------
phone_validator = RegexValidator(
    regex=r'^\+?[0-9]{7,15}$',
    message=_("Enter a valid phone number (7–15 digits, optional +)."),
)


class User(AbstractUser):
    """
    Custom user model built on AbstractUser so we keep username/password
    but make email unique and add phone_number.
    """
    email = models.EmailField(_("email address"), unique=True)
    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        unique=True,
        validators=[phone_validator],
        help_text=_("Include country code, e.g., +94771234567"),
    )

    address_no = models.CharField(
        _("address number"), max_length=20, blank=True, default="")
    address_line1 = models.CharField(
        _("address line 1"), max_length=255, blank=True, default="")
    address_line2 = models.CharField(
        _("address line 2"), max_length=255, blank=True, default="")
    city = models.CharField(_("city"), max_length=100, blank=True, default="")
    postal_code = models.CharField(
        _("postal code"), max_length=20, blank=True, default="")

    customer_id = models.CharField(
        _("Genie customer id"), max_length=64, blank=True, default="", db_index=True)

    # username + password remain from AbstractUser
    # username is the USERNAME_FIELD by default
    REQUIRED_FIELDS = ["email", "phone_number"]


# --- Helpers / mixins --------------------------------------------------------
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# --- Catalog models ----------------------------------------------------------
class Genre(TimestampedModel):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Company(TimestampedModel):
    class CompanyType(models.TextChoices):
        DEVELOPER = "DEVELOPER", _("Developer")
        PUBLISHER = "PUBLISHER", _("Publisher")
        BOTH = "BOTH", _("Developer & Publisher")

    name = models.CharField(max_length=150, unique=True)
    website = models.URLField(blank=True)
    company_type = models.CharField(
        max_length=20, choices=CompanyType.choices, default=CompanyType.BOTH
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(TimestampedModel):
    sku = models.CharField(
        max_length=32, unique=True, default=generate_sku
    )
    title = models.CharField(max_length=255)
    edition = models.CharField(max_length=255, default="Standard Edition")
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField(blank=True)

    genres = models.ManyToManyField(Genre, related_name="products", blank=True)

    developer = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="developed_games",
    )
    publisher = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="published_games",
    )

    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    currency = models.CharField(max_length=3, default="LKR")

    game_size_gb = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=["slug"])]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.sku})"


def product_image_upload_to(instance, filename):
    """
    Store under: media/products/<product-slug-or-title>/<uuid>.<ext>
    """
    base, ext = os.path.splitext(filename)
    product = instance.product
    folder = (product.slug or slugify(product.title)).strip() or "product"
    return f"products/{folder}/{uuid4().hex}{ext.lower()}"


class ProductImage(TimestampedModel):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to=product_image_upload_to)
    alt_text = models.CharField(max_length=150, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "id"]

    def __str__(self):
        return f"Image for {self.product.title}"


class SystemRequirements(TimestampedModel):
    """Minimum (and optional recommended) PC specs for a product."""

    product = models.OneToOneField(
        Product, on_delete=models.CASCADE, related_name="system_requirements"
    )

    # Minimum specs
    min_cpu = models.CharField(max_length=150)
    min_ram_gb = models.PositiveIntegerField()
    min_gpu = models.CharField(max_length=150)
    min_storage_gb = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    min_os = models.CharField(max_length=100, blank=True)

    # Recommended specs (optional)
    rec_cpu = models.CharField(max_length=150, blank=True)
    rec_ram_gb = models.PositiveIntegerField(null=True, blank=True)
    rec_gpu = models.CharField(max_length=150, blank=True)
    rec_storage_gb = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    rec_os = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"System Requirements for {self.product.title}"


class DLC(TimestampedModel):
    product = models.ForeignKey(
        "Product", related_name="dlcs", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to=product_image_upload_to)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.title} (DLC for {self.product.title})"


# --- Cart / Orders -----------------------------------------------------------
class Cart(TimestampedModel):
    """
    LEFT SIDE  = direct game purchases (CartItem through table)
    RIGHT SIDE = one storage device + games selected to be copied onto it (CartStorageItem)
    """
    # Identify the cart (multi-user carts allowed per your original design; anonymous via session_key)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="carts", blank=True)
    session_key = models.CharField(
        max_length=64, blank=True, null=True, help_text="Anonymous session key")

    # LEFT: many products via through-table CartItem
    items = models.ManyToManyField(
        "Product", through="CartItem", related_name="carts", blank=True)

    # RIGHT: at most one storage device for this cart
    storage_device = models.ForeignKey(
        "StorageDevice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="carts",
        help_text="The single storage device (right side) for this cart.",
    )

    def __str__(self):
        uid = ",".join(str(u.id)
                       for u in self.users.all()) or self.session_key or "anon"
        return f"Cart({uid})"

    # --------------------------
    # LEFT SIDE (direct buys)
    # --------------------------
    @property
    def total(self) -> Decimal:
        """Backward-compatible: direct purchases subtotal (left side)."""
        return sum((ci.subtotal for ci in self.cartitem_set.all()), Decimal("0.00"))

    @property
    def direct_total(self) -> Decimal:
        """Alias for clarity in templates/views."""
        return self.total

    # --------------------------
    # RIGHT SIDE (device + its games)
    # --------------------------
    @property
    def storage_device_price(self) -> Decimal:
        return getattr(self.storage_device, "price", Decimal("0.00")) or Decimal("0.00")

    @property
    def storage_games_total(self) -> Decimal:
        return sum((si.subtotal for si in self.cartstorageitem_set.all()), Decimal("0.00"))

    @property
    def storage_total(self) -> Decimal:
        """Right-side subtotal = device price + games copied onto it."""
        return self.storage_device_price + self.storage_games_total

    # --------------------------
    # GRAND TOTAL (everything)
    # --------------------------
    @property
    def grand_total(self) -> Decimal:
        return self.direct_total + self.storage_total

    # --------------------------
    # Capacity (right side only)
    # --------------------------
    @property
    def device_capacity_gb(self) -> Decimal:
        """True usable capacity of the selected device (0 if none)."""
        return getattr(self.storage_device, "true_capacity_gb", None) or Decimal("0")

    @property
    def device_used_gb(self) -> Decimal:
        """Sum of install sizes for games selected to be copied to the device."""
        used = Decimal("0")
        # Select related to avoid N+1 when reading product.game_size_gb
        for si in self.cartstorageitem_set.select_related("product"):
            game_size = si.product.game_size_gb or Decimal("0")
            used += game_size * si.quantity
        return used

    @property
    def device_remaining_gb(self) -> Decimal:
        cap = self.device_capacity_gb
        rem = cap - self.device_used_gb
        return rem if rem > 0 else Decimal("0")

    @property
    def device_percent_used(self) -> Decimal:
        cap = self.device_capacity_gb
        if cap <= 0:
            return Decimal("0")
        pct = (self.device_used_gb / cap) * 100
        # clamp to [0, 100]
        if pct < 0:
            return Decimal("0")
        if pct > 100:
            return Decimal("100")
        return pct


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.quantity} × {self.product.title} in {self.cart}"

    @property
    def subtotal(self) -> Decimal:
        return (self.unit_price or Decimal("0")) * self.quantity


class CartStorageItem(models.Model):
    cart = models.ForeignKey("Cart", on_delete=models.CASCADE)
    product = models.ForeignKey("Product", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)])
    # price for this game when bought on-device
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # per-cart uniqueness for on-device list
        unique_together = ("cart", "product")

    def __str__(self):
        return f"{self.quantity} × {self.product.title} on device in {self.cart}"

    @property
    def subtotal(self):
        return (self.unit_price or Decimal("0")) * self.quantity


class Order(TimestampedModel):
    class OrderStatus(models.TextChoices):
        PAYMENT_INITIATED = "PAYMENT_INITIATED", _("Payment initiated")
        PAYMENT_FAILED = "PAYMENT_FAILED", _("Payment failed")
        PAYMENT_SUCCESS = "PAYMENT_SUCCESS", _("Payment success")
        ORDER_SENT = "ORDER_SENT", _("Order sent")
        ORDER_DELIVERED = "ORDER_DELIVERED", _("Order delivered")
        CANCELLED = "CANCELLED", _("Cancelled")

    class PaymentMethod(models.TextChoices):
        CARD = "CARD", _("Card")
        BANK_TRANSFER = "BANK_TRANSFER", _("Bank transfer")

    # Spec asks for many-to-many with users; typically it is a single user,
    # but we honor the requirement while allowing guest orders via email.
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="orders", blank=True
    )
    guest_email = models.EmailField(blank=True)

    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=30, choices=OrderStatus.choices, default=OrderStatus.PAYMENT_INITIATED
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CARD
    )
    payment_reference = models.CharField(max_length=100, blank=True)

    products = models.ManyToManyField(
        Product, through="OrderItem", related_name="orders"
    )

    storage_device_name = models.CharField(
        max_length=255, blank=True, default="")
    storage_device_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Store the final value at checkout; compute on the fly if not set.
    order_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    currency = models.CharField(max_length=3, default="LKR")

    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Order #{self.id or '—'}"

    @property
    def total(self) -> Decimal:
        computed = sum(
            (item.subtotal for item in self.orderitem_set.all()), Decimal("0.00")
        )
        return self.order_value or computed


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("order", "product")

    def __str__(self):
        return f"{self.quantity} × {self.product.title} in order {self.order_id}"

    @property
    def subtotal(self) -> Decimal:
        return (self.unit_price or Decimal("0")) * self.quantity


class OrderStorageItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="storage_items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("order", "product")

    def __str__(self):
        return f"{self.quantity} × {self.product.title} on device in order {self.order_id}"

    @property
    def subtotal(self) -> Decimal:
        return (self.unit_price or Decimal("0")) * self.quantity


class Ticket(TimestampedModel):
    class Source(models.TextChoices):
        DARAZ = "DARAZ", _("Daraz")
        VIRTUAL_LAB = "VIRTUAL_LAB", _("Virtual Lab website")

    class Status(models.TextChoices):
        OPEN = "OPEN", _("Open")
        IN_PROGRESS = "IN_PROGRESS", _("In progress")
        RESOLVED = "RESOLVED", _("Resolved")
        CLOSED = "CLOSED", _("Closed")

    class Priority(models.TextChoices):
        LOW = "LOW", _("Low")
        NORMAL = "NORMAL", _("Normal")
        HIGH = "HIGH", _("High")

    reference = models.CharField(
        max_length=20, unique=True, default=generate_ticket_ref, editable=False
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="support_tickets", blank=True
    )
    source = models.CharField(max_length=20, choices=Source.choices)

    # Optional link to an order
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL, null=True, blank=True, related_name="tickets"
    )

    subject = models.CharField(max_length=100)  # brief subject (<=100 chars)
    description = models.TextField()

    # Single video attachment (optional)
    video = models.FileField(
        upload_to="tickets/%Y/%m/%d/videos/",
        blank=True,
        null=True,
        validators=[FileExtensionValidator(
            allowed_extensions=["mp4", "mov", "m4v", "webm", "avi"])],
        help_text=_("Upload a single video file (mp4, mov, m4v, webm, avi)."),
    )
    daraz_order_number = models.CharField(max_length=50, blank=True)
    daraz_order_date = models.DateField(null=True, blank=True)

    # Workflow
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.NORMAL)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference}: {self.subject}"

    @property
    def photos_count(self) -> int:
        return self.photos.count()


class TicketPhoto(TimestampedModel):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="tickets/%Y/%m/%d/photos/")
    alt_text = models.CharField(max_length=150, blank=True)

    def __str__(self):
        return f"Photo for {self.ticket.reference}"


class ReservedSlot(TimestampedModel):
    """
    A single 1-hour reservation connected to exactly one Ticket.
    Prevents double-booking the same day/slot via a unique constraint.
    """
    class Slot(models.TextChoices):
        MORNING_09_10 = "09:00-10:00", _("9:00–10:00 AM")
        EVENING_21_22 = "21:00-22:00", _("9:00–10:00 PM")
        EVENING_22_23 = "22:00-23:00", _("10:00–11:00 PM")

    # One reservation per ticket
    ticket = models.OneToOneField(
        Ticket,
        on_delete=models.CASCADE,
        related_name="reservation",
    )

    # Who booked the slot
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reserved_slots",
    )

    # When is the visit and which 1-hour slot
    date = models.DateField()
    slot = models.CharField(max_length=11, choices=Slot.choices)

    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date", "slot"]
        indexes = [
            models.Index(fields=["date", "slot"]),
        ]
        # Ensure a given day+slot can only be reserved once
        unique_together = ("date", "slot")

    def __str__(self):
        return f"{self.date} • {self.get_slot_display()} • {self.user}"


# --- Game Requests -----------------------------------------------------------
class GameRequest(models.Model):
    game_name = models.CharField(max_length=255)
    edition_name = models.CharField(max_length=255, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="game_requests",
    )
    request_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-request_date"]

    def __str__(self):
        who = getattr(self.user, "username", "anonymous")
        suffix = f" • {self.edition_name}" if self.edition_name else ""
        return f"{self.game_name}{suffix} ({who})"


class StorageCategory(models.TextChoices):
    HARD_DISK = "hard_disk", "Hard disk"
    PORTABLE_HARD_DISK = "portable_hard_disk", "Portable hard disk"
    PEN = "pen", "Pen drive"


class StorageDevice(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="LKR")

    # Use GB for both capacities so math stays simple (e.g., 931.51 vs 1000)
    true_capacity_gb = models.DecimalField(
        max_digits=7, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Real usable capacity in GB (e.g., 931.51 for a 1TB drive)."
    )
    marketing_capacity_gb = models.DecimalField(
        max_digits=7, decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Label/box capacity in GB (e.g., 1000.00 for a 1TB drive)."
    )

    image = models.ImageField(
        upload_to="storage_devices/%Y/%m/%d/",
        help_text="16:9 landscape image recommended."
    )

    category = models.CharField(
        max_length=32,
        choices=StorageCategory.choices,
        help_text="Hard disk, Portable hard disk, or Pen drive."
    )

    class Meta:
        ordering = ["category", "true_capacity_gb", "name"]

    def __str__(self):
        return f"{self.name} • {self.get_category_display()}"
