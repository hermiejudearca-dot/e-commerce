
from django.urls import path
from . import views

urlpatterns = [

    # CSRF protection
    path('csrf/', views.csrf, name='store_csrf'),

    # Customer authentication
    path('register/', views.register, name='store_register'),
    path('login/', views.signin, name='store_login'),
    path('logout/', views.signout, name='store_logout'),
    path('me/', views.me, name='store_me'),

    # Shop products
    path('products/', views.products, name='store_products'),

    # Shopping cart
    path('cart/', views.cart, name='store_cart'),

    # Customer favorites
    path('favorites/', views.favorites, name='store_favorites'),

    # Saved delivery addresses
    path('addresses/', views.addresses, name='store_addresses'),

    # Product reviews
    path(
        'reviews/<int:product_id>/',
        views.reviews,
        name='store_reviews'
    ),

    # Customer orders, checkout and Buy Now
    path('orders/', views.orders, name='store_orders'),

]
