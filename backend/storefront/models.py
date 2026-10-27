
from decimal import Decimal

from django.conf import settings
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.db import models
from django.utils import timezone


# ==========================================
# CUSTOMER PROFILE
# ==========================================

class CustomerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_profile",
    )

    full_name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


# ==========================================
# SAVED DELIVERY ADDRESSES
# ==========================================

class DeliveryAddress(models.Model):
    LABEL_CHOICES = [
        ("Home", "Home"),
        ("Work", "Work"),
        ("School", "School"),
        ("Other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_addresses",
    )

    label = models.CharField(
        max_length=20,
        choices=LABEL_CHOICES,
        default="Home",
    )

    recipient = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    street = models.CharField(max_length=255)
    barangay = models.CharField(max_length=120)
    city = models.CharField(max_length=120)
    province = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=12)

    is_default = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="store_one_default_address",
            )
        ]

    @property
    def full_address(self):
        return ", ".join(
            part
            for part in [
                self.street,
                self.barangay,
                self.city,
                self.province,
                self.postal_code,
            ]
            if part
        )

    def __str__(self):
        return f"{self.user_id} - {self.label} - {self.city}"


# ==========================================
# SHOPPING CART
# ==========================================

class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_cart",
    )

    product = models.ForeignKey(
        "product.Product",
        on_delete=models.CASCADE,
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="store_cart_unique",
            )
        ]

    def __str__(self):
        return (
            f"{self.user_id} - "
            f"{self.product_id} x {self.quantity}"
        )


# ==========================================
# FAVORITES
# ==========================================

class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_favorites",
    )

    product = models.ForeignKey(
        "product.Product",
        on_delete=models.CASCADE,
        related_name="store_favorited_by",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"],
                name="store_favorite_unique",
            )
        ]

    def __str__(self):
        return f"{self.user_id} - {self.product_id}"


# ==========================================
# CUSTOMER ORDERS
# ==========================================

class StoreOrder(models.Model):

    # Existing status values are preserved.
    # New statuses allow more detailed tracking.
    STATUS = [
        ("Pending", "Pending"),
        ("Confirmed", "Confirmed"),
        ("Processing", "Processing"),
        ("Preparing", "Preparing"),
        ("Packed", "Packed"),
        ("Shipped", "Shipped"),
        ("In Transit", "In Transit"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivered", "Delivered"),
        ("Completed", "Completed"),
        ("Cancelled", "Cancelled"),
    ]

    PAYMENT_METHODS = [
        ("COD", "Cash on Delivery"),
        ("GCASH", "GCash"),
        ("MAYA", "Maya"),
    ]

    PAYMENT_STATUSES = [
        ("Unpaid", "Unpaid"),
        ("Pending Verification", "Pending Verification"),
        ("Paid", "Paid"),
        ("Failed", "Failed"),
        ("Refunded", "Refunded"),
    ]

    CHECKOUT_MODES = [
        ("cart", "Shopping Cart"),
        ("buy", "Buy Now"),
    ]

    DELIVERY_STATUSES = [
        ("Not Shipped", "Not Shipped"),
        ("Ready for Pickup", "Ready for Pickup"),
        ("Picked Up", "Picked Up"),
        ("In Transit", "In Transit"),
        ("Out for Delivery", "Out for Delivery"),
        ("Delivery Attempted", "Delivery Attempted"),
        ("Delivered", "Delivered"),
        ("Delivery Failed", "Delivery Failed"),
        ("Returned to Sender", "Returned to Sender"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="store_orders",
    )

    # Permanent delivery snapshot.
    recipient = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    address = models.TextField()

    delivery_address = models.ForeignKey(
        DeliveryAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="Pending",
    )

    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHODS,
        default="COD",
    )

    payment_status = models.CharField(
        max_length=25,
        choices=PAYMENT_STATUSES,
        default="Unpaid",
    )

    checkout_mode = models.CharField(
        max_length=10,
        choices=CHECKOUT_MODES,
        default="cart",
    )

    payment_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Product subtotal and delivery fee are
    # stored separately for transparency.
    # Existing order totals are preserved.
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )

    total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    # Manual courier tracking.
    courier_name = models.CharField(
        max_length=120,
        blank=True,
    )

    tracking_number = models.CharField(
        max_length=150,
        blank=True,
    )

    estimated_delivery_start = models.DateField(
        null=True,
        blank=True,
    )

    estimated_delivery_end = models.DateField(
        null=True,
        blank=True,
    )

    delivery_status = models.CharField(
        max_length=25,
        choices=DELIVERY_STATUSES,
        default="Not Shipped",
    )

    # Staff/courier-reported delivery.
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Customer-confirmed receipt.
    received_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Store delivery evidence privately.
    # Do not expose its media URL publicly.
    proof_of_delivery = models.FileField(
        upload_to="delivery_proofs/%Y/%m/",
        null=True,
        blank=True,
    )

    # Optional courier or staff reference.
    delivery_reference = models.CharField(
        max_length=150,
        blank=True,
    )

    policy_accepted_at = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"HB-{self.pk}"

    @property
    def is_delivered(self):
        return self.status in ("Delivered", "Completed")

    @property
    def is_completed(self):
        return self.status == "Completed"

    @property
    def is_paid(self):
        return self.payment_status == "Paid"

    @property
    def customer_confirmed_receipt(self):
        return self.received_at is not None

    @property
    def has_delivery_proof(self):
        return bool(self.proof_of_delivery)


# ==========================================
# ORDER ITEMS
# ==========================================

class StoreOrderItem(models.Model):
    order = models.ForeignKey(
        StoreOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        "product.Product",
        on_delete=models.PROTECT,
    )

    product_name = models.CharField(max_length=200)

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


# ==========================================
# SHIPPING TRACKING HISTORY
# ==========================================

class OrderTrackingEvent(models.Model):

    SOURCE_CHOICES = [
        ("ADMIN", "Admin"),
        ("COURIER", "Courier Integration"),
        ("SYSTEM", "System"),
        ("CUSTOMER", "Customer"),
    ]

    order = models.ForeignKey(
        StoreOrder,
        on_delete=models.CASCADE,
        related_name="tracking_events",
    )

    status = models.CharField(max_length=50)

    message = models.TextField(
        blank=True,
        max_length=1000,
    )

    location = models.CharField(
        max_length=200,
        blank=True,
    )

    source = models.CharField(
        max_length=15,
        choices=SOURCE_CHOICES,
        default="ADMIN",
    )

    # Nullable because automated courier
    # updates may not have a Django user.
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="store_tracking_updates",
    )

    # External courier event ID, reserved for
    # future webhook deduplication.
    external_event_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        unique=True,
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.order} - {self.status}"


# ==========================================
# CUSTOMER RETURN / REFUND REQUESTS
# ==========================================

class OrderIssueRequest(models.Model):

    TYPE_CHOICES = [
        ("Damaged", "Damaged item"),
        ("Incorrect", "Incorrect item"),
        ("Missing", "Missing item"),
        ("Not Received", "Order not received"),
        ("Quality", "Quality concern"),
        ("Return", "Return request"),
        ("Refund", "Refund request"),
        ("Other", "Other"),
    ]

    STATUS_CHOICES = [
        ("Open", "Open"),
        ("Under Review", "Under Review"),
        ("Awaiting Customer", "Awaiting Customer"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
        ("Resolved", "Resolved"),
        ("Closed", "Closed"),
    ]

    order = models.ForeignKey(
        StoreOrder,
        on_delete=models.CASCADE,
        related_name="issue_requests",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="store_issue_requests",
    )

    issue_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
    )

    description = models.TextField(
        max_length=2000,
    )

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default="Open",
    )

    admin_notes = models.TextField(
        blank=True,
    )

    # Evidence requires private storage and
    # authenticated download endpoints.
    evidence = models.FileField(
        upload_to="order_issue_evidence/%Y/%m/",
        null=True,
        blank=True,
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Issue #{self.pk} - "
            f"Order {self.order_id}"
        )


# ==========================================
# VERIFIED PURCHASE PRODUCT REVIEWS
# ==========================================

class ProductReview(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    product = models.ForeignKey(
        "product.Product",
        on_delete=models.CASCADE,
        related_name="store_reviews",
    )

    rating = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ]
    )

    comment = models.TextField(max_length=1500)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(       
                fields=["user", "product"],
                name="store_review_unique",
            )
        ]

        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Review by {self.user_id} "
            f"for product {self.product_id}"
        )
