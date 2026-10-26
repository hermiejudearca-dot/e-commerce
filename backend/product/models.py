
from decimal import Decimal

from django.conf import settings
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to="products/", blank=True)
    category = models.CharField(max_length=30, default="Others")
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Customer(models.Model):
    # Optional for compatibility with existing customer records.
    # New registered customers will be linked to a Django user.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="customer_profile",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Processing", "Processing"),
        ("Shipped", "Shipped"),
        ("Delivered", "Delivered"),
        ("Cancelled", "Cancelled"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Failed", "Failed"),
        ("Refunded", "Refunded"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="orders",
        null=True,
        blank=True,
    )
    address = models.TextField()
    phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="Pending",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="Pending",
    )
    payment_method = models.CharField(max_length=30, blank=True)
    date_ordered = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        customer_name = (
            self.customer.name if self.customer_id else "Guest"
        )
        return f"Order #{self.pk} - {customer_name}"

    @property
    def total_amount(self):
        return sum(
            (item.subtotal for item in self.items.all()),
            Decimal("0.00"),
        )


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price * self.quantity


class CartItem(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "product"],
                name="unique_customer_cart_product",
            ),
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.customer.name}: {self.product.name} x {self.quantity}"


class CartActivity(models.Model):
    ACTION_CHOICES = [
        ("Added", "Added"),
        ("Quantity Updated", "Quantity Updated"),
        ("Removed", "Removed"),
    ]

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        related_name="cart_activities",
        null=True,
        blank=True,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        related_name="cart_activities",
        null=True,
        blank=True,
    )
    product_name = models.CharField(max_length=100)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action}: {self.product_name}"


class Favorite(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="favorites",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="favorited_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["customer", "product"],
                name="unique_customer_favorite_product",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.customer.name} likes {self.product.name}"


class StoreSettings(models.Model):
    # The application uses one settings record, with primary key 1.
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    store_name = models.CharField(max_length=150, default="HONEYBAIL")
    tagline = models.CharField(
        max_length=255,
        default="Small Treats, Big Happiness",
        blank=True,
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    preferences = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.store_name
