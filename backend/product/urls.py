
from django.urls import path
from . import views

app_name = "product"

urlpatterns = [

    # ======================================================
    # PRODUCT MANAGEMENT
    # ======================================================

    # Public product list and product details
    path(
        "products/",
        views.product_list,
        name="product-list",
    ),

    path(
        "products/<int:product_id>/",
        views.product_detail,
        name="product-detail",
    ),

    # Admin product management
    path(
        "admin/products/",
        views.admin_product_list,
        name="admin-product-list",
    ),

    path(
        "admin/products/<int:product_id>/restore/",
        views.restore_product,
        name="restore-product",
    ),

    # ======================================================
    # HONEYBAIL ADMIN DASHBOARD
    # ======================================================

    # Dashboard statistics
    path(
        "dashboard/",
        views.dashboard_stats,
        name="dashboard",
    ),

    # Customer orders from storefront.StoreOrder
    path(
        "orders/",
        views.order_list,
        name="order-list",
    ),

    # Admin order status, payment, courier, and tracking
    path(
        "orders/<int:order_id>/",
        views.order_update,
        name="order-update",
    ),

    # Customer records
    path(
        "customers/",
        views.customer_list,
        name="customer-list",
    ),

    # Sales and order reports
    path(
        "reports/",
        views.reports_data,
        name="reports",
    ),

    # ======================================================
    # AUTHENTICATION
    # ======================================================

    path(
        "csrf/",
        views.csrf_token,
        name="csrf-token",
    ),

    path(
        "auth/register/",
        views.register,
        name="register",
    ),

    path(
        "auth/login/",
        views.login_view,
        name="login",
    ),

    path(
        "auth/logout/",
        views.logout_view,
        name="logout",
    ),

    path(
        "auth/me/",
        views.me,
        name="me",
    ),

    # ======================================================
    # ORIGINAL CART SYSTEM
    # ======================================================

    path(
        "cart/",
        views.cart,
        name="cart",
    ),

    path(
        "cart-activity/",
        views.cart_activity,
        name="cart-activity",
    ),

    # ======================================================
    # FAVORITES
    # ======================================================

    path(
        "favorites/",
        views.favorites,
        name="favorites",
    ),

    # ======================================================
    # STORE SETTINGS
    # ======================================================

    path(
        "settings/",
        views.store_settings,
        name="store-settings",
    ),
]
