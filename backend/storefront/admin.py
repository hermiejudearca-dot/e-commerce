from django.contrib import admin
from .models import CustomerProfile, CartItem, Favorite, StoreOrder, StoreOrderItem, ProductReview

@admin.register(StoreOrder)
class StoreOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'user', 'status', 'total', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('recipient', 'user__email')
    readonly_fields = ('user', 'total', 'policy_accepted_at', 'created_at')

for model in [CustomerProfile, CartItem, Favorite, StoreOrderItem, ProductReview]:
    admin.site.register(model)
