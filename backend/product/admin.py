from django.contrib import admin
from .models import Product, Order, OrderItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "stock",
        "is_active",
        "created_at",
    )
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")
    list_editable = ("price", "stock", "is_active")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer_name",
        "status",
        "payment_status",
        "date_ordered",
    )
    list_filter = ("status", "payment_status", "date_ordered")
    search_fields = ("customer_name", "customer_email")
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "product", "quantity", "unit_price")
    search_fields = ("product__name", "order__customer_name")
