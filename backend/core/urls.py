
from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, HttpResponseNotFound
from django.urls import include, path

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"

STORE_FILE = FRONTEND_DIR / "store.html"
ADMIN_FILE = FRONTEND_DIR / "index.html"


# ==========================================
# FRONTEND PAGE VIEWS
# ==========================================

def serve_html(request, file_path):
    """Serve an HTML page from the frontend folder."""
    if not file_path.is_file():
        return HttpResponseNotFound(
            f"Frontend file not found: {file_path.name}"
        )

    return FileResponse(
        open(file_path, "rb"),
        content_type="text/html; charset=utf-8",
    )


def home(request):
    """Public Honeybail customer storefront."""
    return serve_html(request, STORE_FILE)


def admin_dashboard(request):
    """Custom Honeybail admin dashboard."""
    return serve_html(request, ADMIN_FILE)


# ==========================================
# STOREFRONT ASSETS
# ==========================================

def serve_frontend_asset(request, filename, content_type):
    """Serve a specific CSS or JavaScript file."""
    allowed_files = {
        "store.css",
        "store.js",
    }

    if filename not in allowed_files:
        return HttpResponseNotFound("Asset not found.")

    file_path = FRONTEND_DIR / filename

    if not file_path.is_file():
        return HttpResponseNotFound(
            f"Frontend asset not found: {filename}"
        )

    response = FileResponse(
        open(file_path, "rb"),
        content_type=content_type,
    )

    # Prevent browsers from keeping outdated development assets.
    response["Cache-Control"] = "no-cache"

    return response


def store_css(request):
    return serve_frontend_asset(
        request,
        "store.css",
        "text/css; charset=utf-8",
    )


def store_js(request):
    return serve_frontend_asset(
        request,
        "store.js",
        "application/javascript; charset=utf-8",
    )


# ==========================================
# URL ROUTES
# ==========================================

urlpatterns = [
    # Django built-in administration
    path("admin/", admin.site.urls),

    # Existing product and admin APIs
    path("api/", include("product.urls")),

    # Customer storefront APIs
    path("api/store/", include("storefront.urls")),

    # Storefront CSS and JavaScript
    path("store.css", store_css, name="store-css"),
    path("store.js", store_js, name="store-js"),

    # Public customer homepage
    path("", home, name="home"),

    # Custom Honeybail admin dashboard
    path("dashboard/", admin_dashboard, name="dashboard-page"),

    # Existing admin sections
    path("orders/", admin_dashboard, name="orders-page"),
    path("customers/", admin_dashboard, name="customers-page"),
    path("reports/", admin_dashboard, name="reports-page"),
    path("cart-activity/", admin_dashboard, name="cart-activity-page"),
    path("favorites/", admin_dashboard, name="favorites-page"),
    path("settings/", admin_dashboard, name="settings-page"),
]


# Serve uploaded media during local development.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
