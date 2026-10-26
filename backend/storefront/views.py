
import json
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout, get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from product.models import Product
from .models import (
    CustomerProfile,
    DeliveryAddress,
    CartItem,
    Favorite,
    StoreOrder,
    StoreOrderItem,
    ProductReview,
)


User = get_user_model()


# ==========================================================
# HONEYBAIL STORE SETTINGS
# ==========================================================

FIRST_ITEM_DELIVERY_FEE = Decimal("50.00")
ADDITIONAL_ITEM_DELIVERY_FEE = Decimal("20.00")

# Kept for compatibility with existing frontend responses.
FIXED_DELIVERY_FEE = FIRST_ITEM_DELIVERY_FEE

AVAILABLE_PAYMENT_METHODS = ("COD",)


def calculate_delivery_fee(total_quantity):
    """
    First item: PHP 50
    Each additional item: PHP 20
    """

    if total_quantity <= 0:
        return Decimal("0.00")

    return (
        FIRST_ITEM_DELIVERY_FEE
        + ADDITIONAL_ITEM_DELIVERY_FEE * (total_quantity - 1)
    )


# ==========================================================
# GENERAL HELPERS
# ==========================================================

def err(message, status=400):
    return JsonResponse({"error": message}, status=status)


def payload(request):
    try:
        data = json.loads(request.body or "{}")
    except (ValueError, UnicodeDecodeError):
        return None

    return data if isinstance(data, dict) else None


def customer_required(request):
    return (
        request.user.is_authenticated
        and hasattr(request.user, "store_profile")
    )


def customer_error(request):
    if not customer_required(request):
        return err("Please log in as a customer.", 401)
    return None


def positive_integer(value):
    if isinstance(value, bool):
        return None

    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None

    return number if number >= 1 else None


def clean_string(data, key, max_length):
    value = data.get(key, "")

    if not isinstance(value, str):
        return None

    value = value.strip()

    if len(value) > max_length:
        return None

    return value


def active_products():
    return Product.objects.filter(is_active=True)


def public_product(product):
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "price": str(product.price),
        "stock": product.stock,
        "image": product.image.url if product.image else "",
    }


def serialize_address(address):
    return {
        "id": address.id,
        "label": address.label,
        "recipient": address.recipient,
        "phone": address.phone,
        "street": address.street,
        "barangay": address.barangay,
        "city": address.city,
        "province": address.province,
        "postal_code": address.postal_code,
        "is_default": address.is_default,
        "full_address": address.full_address,
    }


def serialize_order(order):
    items = list(order.items.all())

    subtotal = sum(
        (item.unit_price * item.quantity for item in items),
        Decimal("0.00"),
    )

    recorded_delivery_fee = order.total - subtotal

    return {
        "id": order.id,
        "status": order.status,
        "total": str(order.total),
        "subtotal": str(subtotal),
        "delivery_fee": str(recorded_delivery_fee),
        "date": order.created_at.isoformat(),
        "recipient": order.recipient,
        "phone": order.phone,
        "address": order.address,
        "notes": order.notes,
        "payment_method": order.payment_method,
        "payment_status": order.payment_status,
        "checkout_mode": order.checkout_mode,
        "items": [
            {
                "product_id": item.product_id,
                "name": item.product_name,
                "quantity": item.quantity,
                "price": str(item.unit_price),
                "subtotal": str(item.subtotal),
            }
            for item in items
        ],
    }


# ==========================================================
# CSRF
# ==========================================================

@ensure_csrf_cookie
@require_http_methods(["GET"])
def csrf(request):
    return JsonResponse({"ok": True})


# ==========================================================
# CUSTOMER REGISTRATION
# ==========================================================

@require_http_methods(["POST"])
def register(request):
    data = payload(request)

    if data is None:
        return err("Invalid JSON.")

    name = clean_string(data, "name", 120)
    email = clean_string(data, "email", 254)
    password = data.get("password", "")

    if not name or not email:
        return err("Enter your full name and email.")

    email = email.lower()

    try:
        validate_email(email)
    except ValidationError:
        return err("Enter a valid email address.")

    if not isinstance(password, str) or len(password) < 8:
        return err("Password must be at least 8 characters.")

    if User.objects.filter(email__iexact=email).exists():
        return err("Email is already registered.")

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
            )

            CustomerProfile.objects.create(
                user=user,
                full_name=name,
            )

    except IntegrityError:
        return err("This email is already registered.")

    login(request, user)

    return JsonResponse(
        {
            "customer": {
                "name": name,
                "email": email,
            }
        },
        status=201,
    )


# ==========================================================
# CUSTOMER LOGIN / LOGOUT
# ==========================================================

@require_http_methods(["POST"])
def signin(request):
    data = payload(request)

    if data is None:
        return err("Invalid JSON.")

    email = clean_string(data, "email", 254)
    password = data.get("password", "")

    if not email or not isinstance(password, str):
        return err("Incorrect customer email or password.", 401)

    existing_user = User.objects.filter(
        email__iexact=email.lower()
    ).first()

    if existing_user is None:
        return err("Incorrect customer email or password.", 401)

    user = authenticate(
        request,
        username=existing_user.get_username(),
        password=password,
    )

    if user is None or not hasattr(user, "store_profile"):
        return err("Incorrect customer email or password.", 401)

    login(request, user)

    return JsonResponse({
        "customer": {
            "name": user.store_profile.full_name,
            "email": user.email,
        }
    })


@require_http_methods(["POST"])
def signout(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_http_methods(["GET"])
def me(request):
    if not customer_required(request):
        return JsonResponse({"customer": None})

    return JsonResponse({
        "customer": {
            "name": request.user.store_profile.full_name,
            "email": request.user.email,
        }
    })


# ==========================================================
# PUBLIC PRODUCTS
# ==========================================================

@require_http_methods(["GET"])
def products(request):
    queryset = (
        active_products()
        .annotate(
            average_review_rating=Avg("store_reviews__rating"),
            total_reviews=Count("store_reviews"),
        )
        .order_by("-id")
    )

    result = []

    for product in queryset:
        item = public_product(product)
        item["average_rating"] = round(
            product.average_review_rating or 0,
            1,
        )
        item["review_count"] = product.total_reviews
        result.append(item)

    return JsonResponse({
        "products": result,
        "delivery_fee": str(FIRST_ITEM_DELIVERY_FEE),
        "additional_item_delivery_fee": str(
            ADDITIONAL_ITEM_DELIVERY_FEE
        ),
    })


# ==========================================================
# SHOPPING CART
# ==========================================================

@require_http_methods(["GET", "POST", "PATCH", "DELETE"])
def cart(request):
    denied = customer_error(request)

    if denied:
        return denied

    if request.method == "GET":
        items = list(
            CartItem.objects
            .filter(user=request.user)
            .select_related("product")
            .order_by("id")
        )

        result = []
        subtotal = Decimal("0.00")

        for item in items:
            line_total = item.product.price * item.quantity
            subtotal += line_total

            result.append({
                "id": item.id,
                "quantity": item.quantity,
                "product": public_product(item.product),
                "subtotal": str(line_total),
            })

        total_quantity = sum(
            item.quantity for item in items
        )

        delivery_fee = calculate_delivery_fee(total_quantity)

        return JsonResponse({
            "items": result,
            "total": str(subtotal),
            "subtotal": str(subtotal),
            "total_quantity": total_quantity,
            "delivery_fee": str(delivery_fee),
            "checkout_total": str(subtotal + delivery_fee),
        })

    data = payload(request)

    if data is None:
        return err("Invalid JSON.")

    if request.method == "POST":
        product_id = positive_integer(data.get("product_id"))
        quantity = positive_integer(data.get("quantity", 1))

        if not product_id or not quantity:
            return err("Invalid product or quantity.")

        with transaction.atomic():
            product = (
                active_products()
                .select_for_update()
                .filter(pk=product_id)
                .first()
            )

            if product is None:
                return err("Product unavailable.", 404)

            item = (
                CartItem.objects
                .select_for_update()
                .filter(user=request.user, product=product)
                .first()
            )

            new_quantity = quantity + (
                item.quantity if item else 0
            )

            if new_quantity > product.stock:
                return err("Not enough stock available.")

            if item:
                item.quantity = new_quantity
                item.save(update_fields=["quantity"])
            else:
                CartItem.objects.create(
                    user=request.user,
                    product=product,
                    quantity=quantity,
                )

        return JsonResponse({"ok": True})

    item_id = positive_integer(data.get("item_id"))

    if not item_id:
        return err("Invalid cart item.")

    with transaction.atomic():
        item = (
            CartItem.objects
            .select_for_update()
            .filter(pk=item_id, user=request.user)
            .first()
        )

        if item is None:
            return err("Cart item not found.", 404)

        if request.method == "DELETE":
            item.delete()

        else:
            quantity = positive_integer(data.get("quantity"))

            if not quantity:
                return err("Quantity must be at least 1.")

            product = (
                Product.objects
                .select_for_update()
                .filter(pk=item.product_id)
                .first()
            )

            if (
                product is None
                or not product.is_active
                or quantity > product.stock
            ):
                return err(
                    "Quantity exceeds stock or product unavailable."
                )

            item.quantity = quantity
            item.save(update_fields=["quantity"])

    return JsonResponse({"ok": True})

# ==========================================================
# FAVORITES
# ==========================================================

@require_http_methods(["GET", "POST", "DELETE"])
def favorites(request):
    denied = customer_error(request)

    if denied:
        return denied

    if request.method == "GET":
        items = (
            Favorite.objects
            .filter(user=request.user)
            .select_related("product")
        )

        return JsonResponse({
            "favorites": [
                {"product": public_product(item.product)}
                for item in items
            ]
        })

    data = payload(request)

    if data is None:
        return err("Invalid JSON.")

    product_id = positive_integer(data.get("product_id"))

    if not product_id:
        return err("Invalid product.")

    if request.method == "POST":
        product = active_products().filter(
            pk=product_id
        ).first()

        if product is None:
            return err("Product unavailable.", 404)

        Favorite.objects.get_or_create(
            user=request.user,
            product=product,
        )

        return JsonResponse({
            "ok": True,
            "is_favorite": True,
        })

    Favorite.objects.filter(
        user=request.user,
        product_id=product_id,
    ).delete()

    return JsonResponse({
        "ok": True,
        "is_favorite": False,
    })


# ==========================================================
# SAVED DELIVERY ADDRESSES
# ==========================================================

ADDRESS_FIELDS = {
    "label": 20,
    "recipient": 120,
    "phone": 30,
    "street": 255,
    "barangay": 120,
    "city": 120,
    "province": 120,
    "postal_code": 12,
}

REQUIRED_ADDRESS_FIELDS = [
    "recipient",
    "phone",
    "street",
    "barangay",
    "city",
    "province",
    "postal_code",
]


def validated_address_data(data, existing=None):
    values = {}

    for field, limit in ADDRESS_FIELDS.items():
        if field in data:
            value = clean_string(data, field, limit)

            if value is None:
                return None, f"Invalid or too-long {field}."

            values[field] = value

        elif existing is not None:
            values[field] = getattr(existing, field)

        elif field == "label":
            values[field] = "Home"

        else:
            values[field] = ""

    for field in REQUIRED_ADDRESS_FIELDS:
        if not values[field]:
            return None, (
                f"Please complete {field.replace('_', ' ')}."
            )

    valid_labels = {
        choice[0]
        for choice in DeliveryAddress.LABEL_CHOICES
    }

    if values["label"] not in valid_labels:
        return None, "Invalid address label."

    return values, None


@require_http_methods(["GET", "POST", "PATCH", "DELETE"])
def addresses(request):
    denied = customer_error(request)

    if denied:
        return denied

    # ------------------------------------------------------
    # GET: LIST CUSTOMER ADDRESSES
    # ------------------------------------------------------

    if request.method == "GET":
        items = DeliveryAddress.objects.filter(
            user=request.user
        )

        return JsonResponse({
            "addresses": [
                serialize_address(item)
                for item in items
            ]
        })

    data = payload(request)

    if data is None:
        return err("Invalid JSON.")

    if (
        "is_default" in data
        and not isinstance(data["is_default"], bool)
    ):
        return err("Invalid default-address value.")

    # ------------------------------------------------------
    # POST: ADD NEW ADDRESS
    # ------------------------------------------------------

    if request.method == "POST":
        values, error = validated_address_data(data)

        if error:
            return err(error)

        with transaction.atomic():
            User.objects.select_for_update().get(
                pk=request.user.pk
            )

            existing_count = DeliveryAddress.objects.filter(
                user=request.user
            ).count()

            make_default = (
                data.get("is_default") is True
                or existing_count == 0
            )

            if make_default:
                DeliveryAddress.objects.filter(
                    user=request.user,
                    is_default=True,
                ).update(is_default=False)

            address = DeliveryAddress.objects.create(
                user=request.user,
                is_default=make_default,
                **values,
            )

        return JsonResponse(
            {
                "ok": True,
                "address": serialize_address(address),
            },
            status=201,
        )

    # ------------------------------------------------------
    # PATCH / DELETE: EXISTING ADDRESS
    # ------------------------------------------------------

    address_id = positive_integer(data.get("address_id"))

    if not address_id:
        return err("Invalid address ID.")

    with transaction.atomic():
        User.objects.select_for_update().get(
            pk=request.user.pk
        )

        address = (
            DeliveryAddress.objects
            .select_for_update()
            .filter(
                pk=address_id,
                user=request.user,
            )
            .first()
        )

        if address is None:
            return err("Address not found.", 404)

        # --------------------------------------------------
        # DELETE ADDRESS
        # --------------------------------------------------

        if request.method == "DELETE":
            was_default = address.is_default
            address.delete()

            if was_default:
                replacement = (
                    DeliveryAddress.objects
                    .filter(user=request.user)
                    .order_by("-created_at")
                    .first()
                )

                if replacement:
                    replacement.is_default = True
                    replacement.save(
                        update_fields=["is_default"]
                    )

            return JsonResponse({"ok": True})

        # --------------------------------------------------
        # UPDATE ADDRESS
        # --------------------------------------------------

        values, error = validated_address_data(
            data,
            existing=address,
        )

        if error:
            return err(error)

        make_default = data.get("is_default") is True

        if make_default:
            DeliveryAddress.objects.filter(
                user=request.user,
                is_default=True,
            ).exclude(
                pk=address.pk
            ).update(is_default=False)

        for field, value in values.items():
            setattr(address, field, value)

        if make_default:
            address.is_default = True

        address.save()

    return JsonResponse({
        "ok": True,
        "address": serialize_address(address),
    })

# ==========================================================
# VERIFIED PRODUCT REVIEWS
# ==========================================================

@require_http_methods(["GET", "POST", "DELETE"])
def reviews(request, product_id):
    product = active_products().filter(
        pk=product_id
    ).first()

    if product is None:
        return err("Product not found.", 404)

    # ------------------------------------------------------
    # GET: DISPLAY PRODUCT REVIEWS
    # ------------------------------------------------------

    if request.method == "GET":
        items = (
            ProductReview.objects
            .filter(product=product)
            .select_related("user", "user__store_profile")
            .order_by("-updated_at")
        )

        result = []

        for review in items:
            profile = getattr(
                review.user,
                "store_profile",
                None,
            )

            result.append({
                "name": (
                    profile.full_name if profile else "Customer"
                ),
                "rating": review.rating,
                "comment": review.comment,
                "date": review.updated_at.isoformat(),
                "mine": (
                    request.user.is_authenticated
                    and review.user_id == request.user.id
                ),
            })

        return JsonResponse({"reviews": result})

    # ------------------------------------------------------
    # REQUIRE CUSTOMER LOGIN
    # ------------------------------------------------------

    denied = customer_error(request)

    if denied:
        return denied

    existing_review = ProductReview.objects.filter(
        user=request.user,
        product=product,
    ).first()

    # ------------------------------------------------------
    # DELETE: REMOVE CUSTOMER REVIEW
    # ------------------------------------------------------

    if request.method == "DELETE":
        if existing_review:
            existing_review.delete()

        return JsonResponse({"ok": True})

    # ------------------------------------------------------
    # VERIFY THAT CUSTOMER PURCHASED THE PRODUCT
    # ------------------------------------------------------

    # Customers may only submit reviews after their
    # orders have been marked Delivered.

    purchased = StoreOrderItem.objects.filter(
        order__user=request.user,
        order__status="Delivered",
        product=product,
    ).exists()

    if not purchased:
        return err(
            "You can review this product after your order "
            "has been marked Delivered.",
            403,
        )

    # ------------------------------------------------------
    # VALIDATE REVIEW DATA
    # ------------------------------------------------------

    data = payload(request)

    if data is None:
        return err("Invalid JSON.")

    rating = positive_integer(data.get("rating"))
    comment = clean_string(data, "comment", 1500)

    if (
        rating is None
        or not 1 <= rating <= 5
        or not comment
    ):
        return err(
            "Choose 1–5 stars and write a review "
            "of up to 1500 characters."
        )

    # ------------------------------------------------------
    # CREATE OR UPDATE CUSTOMER REVIEW
    # ------------------------------------------------------

    ProductReview.objects.update_or_create(
        user=request.user,
        product=product,
        defaults={
            "rating": rating,
            "comment": comment,
        },
    )

    return JsonResponse({"ok": True})

# ==========================================================
# CUSTOMER ORDERS + SELECTED CHECKOUT + DISCOUNTED SHIPPING
# ==========================================================

@require_http_methods(["GET", "POST"])
def orders(request):
    denied = customer_error(request)

    if denied:
        return denied

    # ------------------------------------------------------
    # GET: CUSTOMER ORDER HISTORY
    # ------------------------------------------------------

    if request.method == "GET":
        queryset = (
            StoreOrder.objects
            .filter(user=request.user)
            .prefetch_related("items")
            .order_by("-created_at")
        )

        return JsonResponse({
            "orders": [
                serialize_order(order)
                for order in queryset
            ]
        })

    # ------------------------------------------------------
    # POST: CREATE A NEW ORDER
    # ------------------------------------------------------

    data = payload(request)

    if data is None:
        return err("Invalid JSON.")

    payment_method = data.get("payment_method", "COD")

    if payment_method not in AVAILABLE_PAYMENT_METHODS:
        return err(
            "Only Cash on Delivery is currently available."
        )

    if data.get("policy_accepted") is not True:
        return err("Please accept the order policy.")

    checkout_mode = data.get("checkout_mode", "cart")

    if checkout_mode not in ("cart", "buy"):
        return err("Invalid checkout mode.")

    address_id = positive_integer(data.get("address_id"))

    if not address_id:
        return err("Please select a saved delivery address.")

    notes = clean_string(data, "notes", 1000)

    if notes is None:
        return err("Order notes are too long.")

    # ------------------------------------------------------
    # VALIDATE CHECKOUT DETAILS
    # ------------------------------------------------------

    buy_product_id = None
    buy_quantity = None
    selected_cart_item_ids = None

    if checkout_mode == "buy":

        if data.get("selected_cart_item_ids") is not None:
            return err("Invalid Buy Now checkout request.")

        buy_data = data.get("buy_now")

        if not isinstance(buy_data, dict):
            return err("Select a product for Buy Now.")

        buy_product_id = positive_integer(
            buy_data.get("product_id")
        )

        buy_quantity = positive_integer(
            buy_data.get("quantity")
        )

        if not buy_product_id or not buy_quantity:
            return err("Invalid Buy Now product or quantity.")

    else:

        if data.get("buy_now") is not None:
            return err("Invalid cart checkout request.")

        # The updated store.js will send the IDs of
        # the cart items selected by the customer.
        #
        # Example:
        # "selected_cart_item_ids": [2, 5, 7]
        #
        # If the field is omitted, the existing
        # full-cart checkout behavior is preserved.

        if "selected_cart_item_ids" in data:

            raw_ids = data.get("selected_cart_item_ids")

            if not isinstance(raw_ids, list) or not raw_ids:
                return err(
                    "Please select at least one item to checkout."
                )

            selected_cart_item_ids = []

            for raw_id in raw_ids:
                item_id = positive_integer(raw_id)

                if item_id is None:
                    return err("Invalid selected cart item.")

                selected_cart_item_ids.append(item_id)

            if len(selected_cart_item_ids) != len(
                set(selected_cart_item_ids)
            ):
                return err(
                    "Duplicate cart items are not allowed."
                )

    # ------------------------------------------------------
    # DATABASE TRANSACTION
    # ------------------------------------------------------

    with transaction.atomic():

        # Serialize checkout requests from the same customer.

        User.objects.select_for_update().get(
            pk=request.user.pk
        )

        # Verify that the selected delivery address
        # belongs to the logged-in customer.

        selected_address = (
            DeliveryAddress.objects
            .select_for_update()
            .filter(
                pk=address_id,
                user=request.user,
            )
            .first()
        )

        if selected_address is None:
            return err(
                "Selected delivery address is unavailable.",
                404,
            )

        order_items = []
        cart_items = []

        # --------------------------------------------------
        # BUY NOW CHECKOUT
        # --------------------------------------------------

        if checkout_mode == "buy":

            product = (
                Product.objects
                .select_for_update()
                .filter(pk=buy_product_id)
                .first()
            )

            if product is None or not product.is_active:
                return err("Product unavailable.", 404)

            if buy_quantity > product.stock:
                return err("Not enough stock available.")

            order_items.append(
                (product, buy_quantity)
            )

        # --------------------------------------------------
        # SELECTED CART CHECKOUT
        # --------------------------------------------------

        else:

            cart_queryset = (
                CartItem.objects
                .select_for_update()
                .filter(user=request.user)
            )

            # Only checkout the items selected by
            # the customer when IDs are provided.

            if selected_cart_item_ids is not None:
                cart_queryset = cart_queryset.filter(
                    pk__in=selected_cart_item_ids
                )

            cart_items = list(
                cart_queryset.order_by("product_id")
            )

            if not cart_items:
                return err(
                    "Please select at least one item to checkout."
                )

            # Make sure every selected item belongs
            # to this customer's shopping cart.

            if selected_cart_item_ids is not None:

                if len(cart_items) != len(
                    selected_cart_item_ids
                ):
                    return err(
                        "Some selected items are no longer "
                        "in your cart. Please refresh."
                    )

            product_ids = [
                item.product_id
                for item in cart_items
            ]

            # Lock product records to protect stock
            # from concurrent checkout requests.

            locked_products = {
                product.id: product
                for product in (
                    Product.objects
                    .select_for_update()
                    .filter(pk__in=product_ids)
                    .order_by("id")
                )
            }

            for item in cart_items:

                product = locked_products.get(
                    item.product_id
                )

                if (
                    product is None
                    or not product.is_active
                    or item.quantity < 1
                    or item.quantity > product.stock
                ):
                    return err(
                        "Some selected items are unavailable "
                        "or exceed stock. Please update "
                        "your selection."
                    )

                order_items.append(
                    (product, item.quantity)
                )

        # --------------------------------------------------
        # CALCULATE PRODUCT SUBTOTAL
        # --------------------------------------------------

        # Always calculate using actual database prices,
        # never prices submitted by the browser.

        subtotal = sum(
            (
                product.price * quantity
                for product, quantity in order_items
            ),
            Decimal("0.00"),
        )

        # --------------------------------------------------
        # CALCULATE DISCOUNTED SHIPPING
        # --------------------------------------------------

        # First item: PHP 50
        # Each additional item: PHP 20
        #
        # Shipping depends on total quantity,
        # not the number of different products.

        total_quantity = sum(
            quantity
            for product, quantity in order_items
        )

        delivery_fee = calculate_delivery_fee(
            total_quantity
        )

        grand_total = subtotal + delivery_fee

        # --------------------------------------------------
        # CREATE CUSTOMER ORDER
        # --------------------------------------------------

        order = StoreOrder.objects.create(
            user=request.user,
            recipient=selected_address.recipient,
            phone=selected_address.phone,
            address=selected_address.full_address,
            delivery_address=selected_address,
            notes=notes,
            status="Pending",
            payment_method="COD",
            payment_status="Unpaid",
            checkout_mode=checkout_mode,
            subtotal=subtotal,
            delivery_fee=delivery_fee,
            total=grand_total,
            policy_accepted_at=timezone.now(),
        )

        # --------------------------------------------------
        # SAVE PURCHASED ITEMS AND DEDUCT STOCK
        # --------------------------------------------------

        for product, quantity in order_items:

            StoreOrderItem.objects.create(
                order=order,
                product=product,
                product_name=product.name,
                quantity=quantity,
                unit_price=product.price,
            )

            product.stock -= quantity

            product.save(
                update_fields=["stock"]
            )

        # --------------------------------------------------
        # REMOVE ONLY PURCHASED ITEMS FROM CART
        # --------------------------------------------------

        # Buy Now never removes items from the cart.
        #
        # Cart checkout removes only the purchased
        # cart items. Unselected items remain saved.

        if checkout_mode == "cart":

            purchased_cart_item_ids = [
                item.pk
                for item in cart_items
            ]

            CartItem.objects.filter(
                user=request.user,
                pk__in=purchased_cart_item_ids,
            ).delete()

    # ------------------------------------------------------
    # RETURN SUCCESSFUL ORDER RESPONSE
    # ------------------------------------------------------

    return JsonResponse(
        {
            "ok": True,
            "order_id": order.pk,
            "subtotal": str(subtotal),
            "total_quantity": total_quantity,
            "delivery_fee": str(delivery_fee),
            "total": str(grand_total),
            "payment_method": "COD",
            "payment_status": "Unpaid",
            "checkout_mode": checkout_mode,
            "status": "Pending",
        },
        status=201,
    )
