
from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import FileResponse, HttpResponseNotFound
from django.urls import include, path

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_FILE = BASE_DIR.parent / "frontend" / "index.html"


def home(request):
    if not FRONTEND_FILE.exists():
        return HttpResponseNotFound(
            f"Frontend file not found: {FRONTEND_FILE}"
        )

    return FileResponse(
        open(FRONTEND_FILE, "rb"),
        content_type="text/html",
    )


urlpatterns = [
    # Django administration
    path("admin/", admin.site.urls),

    # Existing Honeybail admin and product APIs
    path("api/", include("product.urls")),

    # NEW: Honeybail customer storefront APIs
    path("api/store/", include("storefront.urls")),

    # Honeybail admin frontend
    path("", home, name="home"),

    # Optional direct URLs for the admin sections
    path("dashboard/", home, name="dashboard-page"),
    path("orders/", home, name="orders-page"),
    path("customers/", home, name="customers-page"),
    path("reports/", home, name="reports-page"),
    path("cart-activity/", home, name="cart-activity-page"),
    path("favorites/", home, name="favorites-page"),
    path("settings/", home, name="settings-page"),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
