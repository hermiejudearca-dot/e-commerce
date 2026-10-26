from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


def home(request):
    return redirect("http://127.0.0.1:5500/index.html")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("product.urls")),
    path("", home, name="home"),
]