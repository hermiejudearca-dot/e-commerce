from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from product.views import product_list


def home(request):
    return JsonResponse({
        "message": "Welcome to HONEYBAIL E-commerce Backend!",
        "status": "running",
        "endpoints": {
            "admin": "/admin/",
            "products": "/api/products/"
        }
    })


urlpatterns = [
    path("", home, name="home"),
    path("admin/", admin.site.urls),
    path("api/products/", product_list, name="product_list"),
]
