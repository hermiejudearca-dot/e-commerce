
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import (
    Product,
    Customer,
    Order,
    OrderItem,
    CartItem,
    CartActivity,
    Favorite,
    StoreSettings,
)

from storefront.models import (
    CustomerProfile,
    StoreOrder,
    StoreOrderItem,
    OrderTrackingEvent,
)

User = get_user_model()


# ==========================================================
# GENERAL HELPERS
# ==========================================================

def json_error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def request_data(request):
    if request.content_type and request.content_type.startswith(
        "multipart/form-data"
    ):
        return request.POST

    if not request.body:
        return {}

    try:
        return json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def customer_for_request(request):
    if not request.user.is_authenticated:
        return None

    try:
        return request.user.customer_profile
    except Customer.DoesNotExist:
        return None


def require_customer(request):
    if not request.user.is_authenticated:
        return None, json_error("Please log in first.", 401)

    customer = customer_for_request(request)

    if customer is None:
        return None, json_error(
            "This account has no customer profile.", 403
        )

    return customer, None


def require_staff(request):
    if not request.user.is_authenticated:
        return json_error("Please log in first.", 401)

    if not request.user.is_active or not request.user.is_staff:
        return json_error("Staff permission required.", 403)

    return None


def positive_int(value):
    if isinstance(value, bool):
        return None

    try:
        number = int(value)
        return number if number > 0 else None
    except (ValueError, TypeError, OverflowError):
        return None


# ==========================================================
# PRODUCT HELPERS
# ==========================================================

def serialize_product(request, product):
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "description": product.description,
        "price": str(product.price),
        "stock": product.stock,
        "is_active": product.is_active,
        "image": (
            request.build_absolute_uri(product.image.url)
            if product.image else None
        ),
    }


def validate_product_data(data, partial=False):
    if data is None or not hasattr(data, "get"):
        return "Request body must be valid JSON or form data."

    if not partial:
        required = ("name", "price", "stock")
        missing = [
            field for field in required
            if not str(data.get(field, "")).strip()
        ]
        if missing:
            return "Missing required field(s): " + ", ".join(missing)

    if "name" in data and not str(data["name"]).strip():
        return "Product name cannot be empty."

    if "price" in data:
        try:
            price = Decimal(str(data["price"]))
            if not price.is_finite() or price < 0:
                return "Price must be a finite, non-negative number."
            if price.as_tuple().exponent < -2:
                return "Price can have at most two decimal places."
            if price >= Decimal("100000000"):
                return "Price is too large."
        except (InvalidOperation, TypeError, ValueError):
            return "Price must be a valid number."

    if "stock" in data:
        try:
            raw = str(data["stock"]).strip()
            stock = int(raw)
            if raw != str(stock) or stock < 0:
                return "Stock must be a non-negative whole number."
        except (ValueError, TypeError):
            return "Stock must be a non-negative whole number."

    return None


def apply_product_data(product, data, request):
    for field in ("name", "category", "description"):
        if field in data:
            setattr(product, field, str(data.get(field, "")).strip())

    if "price" in data:
        product.price = Decimal(str(data["price"]))

    if "stock" in data:
        product.stock = int(data["stock"])

    if "image" in request.FILES:
        product.image = request.FILES["image"]


# ==========================================================
# PRODUCTS
# ==========================================================

@require_http_methods(["GET", "POST"])
def product_list(request):
    if request.method == "GET":
        products = Product.objects.filter(
            is_active=True
        ).order_by("id")

        return JsonResponse({
            "products": [
                serialize_product(request, p)
                for p in products
            ]
        })

    permission_error = require_staff(request)
    if permission_error:
        return permission_error

    data = request_data(request)
    error = validate_product_data(data)

    if error:
        return json_error(error)

    product = Product()
    apply_product_data(product, data, request)
    product.save()

    return JsonResponse(
        {"product": serialize_product(request, product)},
        status=201,
    )


@require_http_methods(["GET", "POST", "PUT", "PATCH", "DELETE"])
def product_detail(request, product_id):
    if request.method != "GET":
        permission_error = require_staff(request)
        if permission_error:
            return permission_error

    try:
        product = Product.objects.get(
            pk=product_id,
            is_active=True,
        )
    except Product.DoesNotExist:
        return json_error("Product not found.", 404)

    if request.method == "GET":
        return JsonResponse({
            "product": serialize_product(request, product)
        })

    if request.method == "DELETE":
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])
        return JsonResponse({"message": "Product archived."})

    data = request_data(request)
    error = validate_product_data(data, partial=True)

    if error:
        return json_error(error)

    apply_product_data(product, data, request)
    product.save()

    return JsonResponse({
        "product": serialize_product(request, product)
    })


@require_http_methods(["GET"])
def admin_product_list(request):
    permission_error = require_staff(request)
    if permission_error:
        return permission_error

    products = Product.objects.all().order_by("id")

    return JsonResponse({
        "products": [
            serialize_product(request, p)
            for p in products
        ]
    })


@require_http_methods(["POST"])
def restore_product(request, product_id):
    permission_error = require_staff(request)
    if permission_error:
        return permission_error

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return json_error("Product not found.", 404)

    product.is_active = True
    product.save(update_fields=["is_active", "updated_at"])

    return JsonResponse({
        "message": "Product restored.",
        "product": serialize_product(request, product),
    })


# ==========================================================
# STOREFRONT ORDERS - ADMIN
# ==========================================================

ORDER_PROGRESS = [
    "Pending",
    "Confirmed",
    "Processing",
    "Preparing",
    "Packed",
    "Shipped",
    "In Transit",
    "Out for Delivery",
    "Delivered",
]

DELIVERY_STATUS_MAP = {
    "Pending": "Not Shipped",
    "Confirmed": "Not Shipped",
    "Processing": "Not Shipped",
    "Preparing": "Not Shipped",
    "Packed": "Ready for Pickup",
    "Shipped": "Picked Up",
    "In Transit": "In Transit",
    "Out for Delivery": "Out for Delivery",
    "Delivered": "Delivered",
}

DELIVERY_STATUSES = {
    value for value, _ in StoreOrder.DELIVERY_STATUSES
}

PAYMENT_STATUSES = {
    value for value, _ in StoreOrder.PAYMENT_STATUSES
}


def serialize_order(order):
    items = list(order.items.all())

    subtotal = sum(
        (
            item.unit_price * item.quantity
            for item in items
        ),
        Decimal("0.00"),
    )

    profile = getattr(order.user, "store_profile", None)
    customer_name = (
        profile.full_name if profile else order.recipient
    )

    return {
        "id": order.id,
        "order_number": f"HB-{order.id:04d}",
        "customer": customer_name,
        "customer_name": customer_name,
        "customer_id": order.user_id,
        "customer_email": order.user.email,
        "recipient": order.recipient,
        "address": order.address,
        "phone": order.phone,
        "notes": order.notes,
        "status": order.status,
        "delivery_status": order.delivery_status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "payment_reference": order.payment_reference,
        "checkout_mode": order.checkout_mode,
        "items_count": sum(i.quantity for i in items),
        "subtotal": str(subtotal),
        "delivery_fee": str(order.total - subtotal),
        "total": str(order.total),
        "total_amount": str(order.total),
        "date_ordered": order.created_at.isoformat(),
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        "courier_name": order.courier_name,
        "tracking_number": order.tracking_number,
        "estimated_delivery_start": (
            order.estimated_delivery_start.isoformat()
            if order.estimated_delivery_start else None
        ),
        "estimated_delivery_end": (
            order.estimated_delivery_end.isoformat()
            if order.estimated_delivery_end else None
        ),
        "delivered_at": (
            order.delivered_at.isoformat()
            if order.delivered_at else None
        ),
        "received_at": (
            order.received_at.isoformat()
            if order.received_at else None
        ),
        "has_delivery_proof": bool(order.proof_of_delivery),
        "items": [
            {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "name": item.product_name,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "subtotal": str(item.subtotal),
            }
            for item in items
        ],
        "tracking_events": [
            {
                "id": event.id,
                "status": event.status,
                "message": event.message,
                "location": event.location,
                "source": event.source,
                "created_at": event.created_at.isoformat(),
            }
            for event in order.tracking_events.all()
        ],
    }


def admin_orders_queryset():
    return (
        StoreOrder.objects
        .select_related("user", "user__store_profile")
        .prefetch_related("items", "tracking_events")
        .order_by("-created_at")
    )


def paid_sales_total():
    result = StoreOrder.objects.filter(
        payment_status="Paid"
    ).aggregate(total=Sum("total"))

    return result["total"] or Decimal("0.00")


@require_http_methods(["GET"])
def dashboard_stats(request):
    permission_error = require_staff(request)
    if permission_error:
        return permission_error

    return JsonResponse({
        "dashboard": {
            "total_orders": StoreOrder.objects.count(),
            "total_sales": str(paid_sales_total()),
            "total_products": Product.objects.filter(
                is_active=True
            ).count(),
            "total_customers": CustomerProfile.objects.count(),
            "pending_orders": StoreOrder.objects.filter(
                status="Pending"
            ).count(),
            "shipped_orders": StoreOrder.objects.filter(
                status__in=[
                    "Shipped",
                    "In Transit",
                    "Out for Delivery",
                ]
            ).count(),
        }
    })


@require_http_methods(["GET"])
def order_list(request):
    permission_error = require_staff(request)
    if permission_error:
        return permission_error

    return JsonResponse({
        "orders": [
            serialize_order(order)
            for order in admin_orders_queryset()
        ]
    })


@require_http_methods(["PATCH"])
def order_update(request, order_id):
    permission_error = require_staff(request)
    if permission_error:
        return permission_error

    data = request_data(request)

    if not isinstance(data, dict):
        return json_error("Request body must be valid JSON.")

    allowed_fields = {
        "status",
        "payment_status",
        "delivery_status",
        "courier_name",
        "tracking_number",
        "estimated_delivery_start",
        "estimated_delivery_end",
        "tracking_message",
        "tracking_location",
    }

    if not data or set(data) - allowed_fields:
        return json_error("Unsupported order update fields.")

    text_limits = {
        "courier_name": 120,
        "tracking_number": 150,
        "tracking_message": 1000,
        "tracking_location": 200,
    }

    for field, limit in text_limits.items():
        if field in data:
            if (
                not isinstance(data[field], str)
                or len(data[field]) > limit
            ):
                return json_error(f"Invalid {field}.")

    parsed_dates = {}

    for field in (
        "estimated_delivery_start",
        "estimated_delivery_end",
    ):
        if field in data:
            value = data[field]

            if value is None or value == "":
                parsed_dates[field] = None
            elif isinstance(value, str):
                try:
                    parsed_dates[field] = date.fromisoformat(value)
                except ValueError:
                    return json_error(
                        f"{field} must use YYYY-MM-DD."
                    )
            else:
                return json_error(f"Invalid {field}.")

    with transaction.atomic():
        order = (
            StoreOrder.objects
            .select_for_update()
            .filter(pk=order_id)
            .first()
        )

        if order is None:
            return json_error("Order not found.", 404)

        if order.status in ("Cancelled", "Completed"):
            return json_error(
                "Cancelled or completed orders cannot be "
                "modified through this endpoint.",
                409,
            )

        previous_status = order.status
        previous_delivery = order.delivery_status

        if "status" in data:
            new_status = data["status"]

            if new_status not in ORDER_PROGRESS:
                return json_error(
                    "Invalid status. Cancellation and completion "
                    "require separate workflows."
                )

            if previous_status not in ORDER_PROGRESS:
                return json_error(
                    "Current status cannot be advanced.",
                    409,
                )

            old_index = ORDER_PROGRESS.index(previous_status)
            new_index = ORDER_PROGRESS.index(new_status)

            if new_index < old_index:
                return json_error(
                    "Order status cannot move backwards.",
                    409,
                )

            if new_index > old_index + 1:
                return json_error(
                    "Advance the order one stage at a time.",
                    409,
                )

            order.status = new_status

            if new_status != previous_status:
                order.delivery_status = DELIVERY_STATUS_MAP[
                    new_status
                ]

                if new_status == "Delivered":
                    order.delivered_at = timezone.now()

        if "delivery_status" in data:
            new_delivery = data["delivery_status"]

            if new_delivery not in DELIVERY_STATUSES:
                return json_error("Invalid delivery status.")

            if (
                new_delivery == "Delivered"
                and order.status != "Delivered"
            ):
                return json_error(
                    "Advance the order to Delivered first."
                )

            order.delivery_status = new_delivery

        if "payment_status" in data:
            new_payment = data["payment_status"]

            if new_payment not in PAYMENT_STATUSES:
                return json_error("Invalid payment status.")

            if new_payment == "Refunded":
                return json_error(
                    "Refunds require a separate refund workflow."
                )

            if new_payment == "Paid":
                if order.payment_method != "COD":
                    return json_error(
                        "Online payments require verified "
                        "payment integration."
                    )

                if order.status != "Delivered":
                    return json_error(
                        "Confirm COD collection after delivery "
                        "before marking payment as Paid."
                    )

                if order.payment_status != "Paid":
                    order.paid_at = timezone.now()

            elif order.payment_status == "Paid":
                return json_error(
                    "Paid orders cannot be reverted here."
                )

            order.payment_status = new_payment

        for field in ("courier_name", "tracking_number"):
            if field in data:
                setattr(order, field, data[field].strip())

        for field, value in parsed_dates.items():
            setattr(order, field, value)

        if (
            order.estimated_delivery_start
            and order.estimated_delivery_end
            and order.estimated_delivery_start
            > order.estimated_delivery_end
        ):
            return json_error(
                "Estimated delivery start cannot be "
                "after the end date."
            )

        tracking_changed = (
            order.status != previous_status
            or order.delivery_status != previous_delivery
        )

        message = data.get("tracking_message", "").strip()
        location = data.get("tracking_location", "").strip()

        order.save()

        if tracking_changed or message:
            OrderTrackingEvent.objects.create(
                order=order,
                status=order.status,
                message=(
                    message
                    or f"Order status updated to {order.status}."
                ),
                location=location,
                source="ADMIN",
                updated_by=request.user,
            )

    updated_order = (
        admin_orders_queryset()
        .filter(pk=order_id)
        .first()
    )

    return JsonResponse({
        "ok": True,
        "order": serialize_order(updated_order),
    })


# ==========================================================
# ADMIN CUSTOMERS
# ==========================================================

@require_http_methods(["GET"])
def customer_list(request):
    permission_error = require_staff(request)
    if permission_error:
        return permission_error

    profiles = (
        CustomerProfile.objects
        .select_related("user")
        .order_by("-created_at")
    )

    return JsonResponse({
        "customers": [
            {
                "id": profile.user_id,
                "name": profile.full_name,
                "email": profile.user.email,
                "created_at": profile.created_at.isoformat(),
            }
            for profile in profiles
        ]
    })


# ==========================================================
# ADMIN REPORTS
# ==========================================================

@require_http_methods(["GET"])
def reports_data(request):
    permission_error = require_staff(request)
    if permission_error:
        return permission_error

    sales_by_month = (
        StoreOrder.objects
        .filter(payment_status="Paid")
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total_sales=Sum("total"))
        .order_by("month")
    )

    top_products = (
        StoreOrderItem.objects
        .filter(order__payment_status="Paid")
        .values("product_id", "product_name")
        .annotate(units_sold=Sum("quantity"))
        .order_by("-units_sold")[:5]
    )

    return JsonResponse({
        "report": {
            "total_orders": StoreOrder.objects.count(),
            "total_sales": str(paid_sales_total()),
            "paid_orders": StoreOrder.objects.filter(
                payment_status="Paid"
            ).count(),
            "pending_orders": StoreOrder.objects.filter(
                status="Pending"
            ).count(),
            "sales_by_month": [
                {
                    "month": row["month"].strftime("%B %Y"),
                    "total_sales": str(
                        row["total_sales"] or Decimal("0.00")
                    ),
                }
                for row in sales_by_month
                if row["month"] is not None
            ],
            "top_products": [
                {
                    "product_id": row["product_id"],
                    "product_name": row["product_name"],
                    "units_sold": row["units_sold"],
                }
                for row in top_products
            ],
        }
    })


# ==========================================================
# ORIGINAL CUSTOMER AUTHENTICATION API
# ==========================================================

@ensure_csrf_cookie
@require_http_methods(["GET"])
def csrf_token(request):
    return JsonResponse({"message": "CSRF cookie set."})


@require_http_methods(["POST"])
def register(request):
    data = request_data(request)

    if not isinstance(data, dict):
        return json_error("Request body must be valid JSON.")

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not name or not email or not isinstance(password, str):
        return json_error(
            "Name, email, and password are required."
        )

    if len(password) < 8:
        return json_error(
            "Password must be at least 8 characters."
        )

    if User.objects.filter(username__iexact=email).exists():
        return json_error(
            "An account with this email already exists.",
            409,
        )

    if Customer.objects.filter(email__iexact=email).exists():
        return json_error(
            "A customer record with this email already exists.",
            409,
        )

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=name[:150],
            )

            customer = Customer.objects.create(
                user=user,
                name=name,
                email=email,
            )
    except IntegrityError:
        return json_error(
            "An account with this email already exists.",
            409,
        )

    login(request, user)

    return JsonResponse({
        "message": "Account created successfully.",
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
        },
    }, status=201)


@require_http_methods(["POST"])
def login_view(request):
    data = request_data(request)

    if not isinstance(data, dict):
        return json_error("Request body must be valid JSON.")

    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not email or not isinstance(password, str):
        return json_error(
            "Email and password are required."
        )

    user = authenticate(
        request,
        username=email,
        password=password,
    )

    if user is None:
        return json_error(
            "Invalid email or password.",
            401,
        )

    if not user.is_active:
        return json_error(
            "This account is disabled.",
            403,
        )

    login(request, user)
    customer = customer_for_request(request)

    return JsonResponse({
        "message": "Login successful.",
        "user": {
            "id": user.id,
            "email": user.email,
            "is_staff": user.is_staff,
        },
        "customer": (
            {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
            }
            if customer else None
        ),
    })


@require_http_methods(["POST"])
def logout_view(request):
    logout(request)
    return JsonResponse({
        "message": "Logged out successfully."
    })


@require_http_methods(["GET"])
def me(request):
    if not request.user.is_authenticated:
        return json_error("Please log in first.", 401)

    customer = customer_for_request(request)

    return JsonResponse({
        "user": {
            "id": request.user.id,
            "email": request.user.email,
            "is_staff": request.user.is_staff,
        },
        "customer": (
            {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
            }
            if customer else None
        ),
    })


# ==========================================================
# ORIGINAL CUSTOMER CART API
# ==========================================================

def log_cart_activity(customer, product, action, quantity):
    CartActivity.objects.create(
        customer=customer,
        product=product,
        product_name=product.name,
        action=action,
        quantity=quantity,
    )


def serialize_cart_item(item):
    return {
        "id": item.id,
        "product": {
            "id": item.product_id,
            "name": item.product.name,
            "category": item.product.category,
            "price": str(item.product.price),
            "stock": item.product.stock,
            "image": (
                item.product.image.url
                if item.product.image else None
            ),
        },
        "quantity": item.quantity,
        "subtotal": str(
            item.product.price * item.quantity
        ),
        "updated_at": item.updated_at.isoformat(),
    }


@require_http_methods(["GET", "POST", "PATCH", "DELETE"])
def cart(request):
    customer, error = require_customer(request)

    if error:
        return error

    if request.method == "GET":
        items = list(
            CartItem.objects.filter(
                customer=customer,
                product__is_active=True,
            ).select_related("product")
        )

        total = sum(
            (
                item.product.price * item.quantity
                for item in items
            ),
            Decimal("0.00"),
        )

        return JsonResponse({
            "items": [
                serialize_cart_item(item)
                for item in items
            ],
            "total": str(total),
        })

    data = request_data(request)

    if not isinstance(data, dict):
        return json_error("Request body must be valid JSON.")

    if request.method == "POST":
        product_id = positive_int(data.get("product_id"))
        quantity = positive_int(data.get("quantity", 1))

        if not product_id or not quantity:
            return json_error(
                "Valid product_id and quantity are required."
            )

        with transaction.atomic():
            product = (
                Product.objects
                .select_for_update()
                .filter(pk=product_id, is_active=True)
                .first()
            )

            if product is None:
                return json_error("Product not found.", 404)

            if quantity > product.stock:
                return json_error(
                    "Requested quantity exceeds available stock."
                )

            item = (
                CartItem.objects
                .select_for_update()
                .filter(customer=customer, product=product)
                .first()
            )

            created = item is None

            if created:
                item = CartItem.objects.create(
                    customer=customer,
                    product=product,
                    quantity=quantity,
                )
                log_cart_activity(
                    customer, product, "Added", quantity
                )
            else:
                new_quantity = item.quantity + quantity

                if new_quantity > product.stock:
                    return json_error(
                        "Requested quantity exceeds available stock."
                    )

                item.quantity = new_quantity
                item.save(
                    update_fields=["quantity", "updated_at"]
                )

                log_cart_activity(
                    customer,
                    product,
                    "Quantity Updated",
                    new_quantity,
                )

        return JsonResponse({
            "item": serialize_cart_item(item),
            "message": "Cart updated.",
        }, status=201 if created else 200)

    item_id = positive_int(data.get("item_id"))

    if not item_id:
        return json_error("A valid item_id is required.")

    with transaction.atomic():
        item = (
            CartItem.objects
            .select_for_update()
            .select_related("product")
            .filter(pk=item_id, customer=customer)
            .first()
        )

        if item is None:
            return json_error("Cart item not found.", 404)

        if request.method == "PATCH":
            quantity = positive_int(data.get("quantity"))

            if not quantity:
                return json_error(
                    "A valid quantity is required."
                )

            if (
                not item.product.is_active
                or quantity > item.product.stock
            ):
                return json_error(
                    "Quantity exceeds available stock."
                )

            item.quantity = quantity
            item.save(
                update_fields=["quantity", "updated_at"]
            )

            log_cart_activity(
                customer,
                item.product,
                "Quantity Updated",
                quantity,
            )

            return JsonResponse({
                "item": serialize_cart_item(item)
            })

        log_cart_activity(
            customer,
            item.product,
            "Removed",
            item.quantity,
        )
        item.delete()

    return JsonResponse({
        "message": "Item removed from cart."
    })


# ==========================================================
# ADMIN CART ACTIVITY
# ==========================================================

@require_http_methods(["GET"])
def cart_activity(request):
    permission_error = require_staff(request)

    if permission_error:
        return permission_error

    activities = (
        CartActivity.objects
        .select_related("customer", "product")
        .all()[:500]
    )

    return JsonResponse({
        "activities": [
            {
                "id": activity.id,
                "customer": (
                    activity.customer.name
                    if activity.customer
                    else "Deleted customer"
                ),
                "product_id": activity.product_id,
                "product_name": activity.product_name,
                "action": activity.action,
                "quantity": activity.quantity,
                "created_at": (
                    activity.created_at.isoformat()
                ),
            }
            for activity in activities
        ]
    })


# ==========================================================
# ORIGINAL CUSTOMER FAVORITES API
# ==========================================================

@require_http_methods(["GET", "POST", "DELETE"])
def favorites(request):
    customer, error = require_customer(request)

    if error:
        return error

    if request.method == "GET":
        items = (
            Favorite.objects
            .filter(
                customer=customer,
                product__is_active=True,
            )
            .select_related("product")
        )

        return JsonResponse({
            "favorites": [
                {
                    "id": item.id,
                    "product": serialize_product(
                        request,
                        item.product,
                    ),
                    "created_at": item.created_at.isoformat(),
                }
                for item in items
            ]
        })

    data = request_data(request)

    if not isinstance(data, dict):
        return json_error("Request body must be valid JSON.")

    product_id = positive_int(data.get("product_id"))

    if not product_id:
        return json_error(
            "A valid product_id is required."
        )

    if request.method == "POST":
        product = Product.objects.filter(
            pk=product_id,
            is_active=True,
        ).first()

        if product is None:
            return json_error("Product not found.", 404)

        favorite, created = Favorite.objects.get_or_create(
            customer=customer,
            product=product,
        )

        return JsonResponse({
            "message": (
                "Favorite added."
                if created else "Already a favorite."
            ),
            "favorite_id": favorite.id,
        }, status=201 if created else 200)

    deleted, _ = Favorite.objects.filter(
        customer=customer,
        product_id=product_id,
    ).delete()

    if not deleted:
        return json_error("Favorite not found.", 404)

    return JsonResponse({
        "message": "Favorite removed."
    })


# ==========================================================
# STORE SETTINGS
# ==========================================================

@require_http_methods(["GET", "PUT", "PATCH"])
def store_settings(request):
    permission_error = require_staff(request)

    if permission_error:
        return permission_error

    settings_obj, _ = StoreSettings.objects.get_or_create(
        pk=1
    )

    if request.method == "GET":
        return JsonResponse({
            "settings": {
                "store_name": settings_obj.store_name,
                "tagline": settings_obj.tagline,
                "email": settings_obj.email,
                "phone": settings_obj.phone,
                "address": settings_obj.address,
                "preferences": settings_obj.preferences,
                "updated_at": (
                    settings_obj.updated_at.isoformat()
                ),
            }
        })

    data = request_data(request)

    if not isinstance(data, dict):
        return json_error(
            "Request body must be valid JSON."
        )

    allowed = {
        "store_name",
        "tagline",
        "email",
        "phone",
        "address",
        "preferences",
    }

    unknown = set(data) - allowed

    if unknown:
        return json_error(
            "Unsupported field(s): "
            + ", ".join(sorted(unknown))
        )

    for field in (
        "store_name",
        "tagline",
        "email",
        "phone",
        "address",
    ):
        if field in data:
            value = data[field]

            if not isinstance(value, str):
                return json_error(
                    f"{field} must be a string."
                )

            setattr(settings_obj, field, value.strip())

    if "preferences" in data:
        if not isinstance(data["preferences"], dict):
            return json_error(
                "preferences must be a JSON object."
            )

        settings_obj.preferences = data["preferences"]

    if not settings_obj.store_name:
        return json_error(
            "Store name cannot be empty."
        )

    settings_obj.save()

    return JsonResponse({
        "message": "Store settings saved.",
        "settings": {
            "store_name": settings_obj.store_name,
            "tagline": settings_obj.tagline,
            "email": settings_obj.email,
            "phone": settings_obj.phone,
            "address": settings_obj.address,
            "preferences": settings_obj.preferences,
            "updated_at": (
                settings_obj.updated_at.isoformat()
            ),
        },
    })
