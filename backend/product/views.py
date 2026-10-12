
from django.http import JsonResponse
from .models import Product


def product_list(request):
    if request.method != "GET":
        return JsonResponse(
            {"error": "Only GET requests are allowed."},
            status=405
        )

    products = Product.objects.filter(is_active=True).order_by("id")

    data = []

    for product in products:
        data.append({
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "description": product.description,
            "price": str(product.price),
            "stock": product.stock,
            "image": (
                request.build_absolute_uri(product.image.url)
                if product.image
                else None
            ),
        })

    return JsonResponse({"products": data})

