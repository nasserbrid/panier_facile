"""
Administration Django pour les modèles supermarkets.
"""
from django.contrib import admin
from .models import LeclercProductMatch, AldiProductMatch, PriceComparison


@admin.register(LeclercProductMatch)
class LeclercProductMatchAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'product_name', 'price', 'store_id', 'is_available', 'last_updated')
    list_filter = ('is_available', 'store_id')
    search_fields = ('ingredient__nom', 'product_name')
    readonly_fields = ('created_at', 'last_updated')


@admin.register(AldiProductMatch)
class AldiProductMatchAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'product_name', 'price', 'store_id', 'is_available', 'last_updated')
    list_filter = ('is_available', 'store_id')
    search_fields = ('ingredient__nom', 'product_name')
    readonly_fields = ('created_at', 'last_updated')


@admin.register(PriceComparison)
class PriceComparisonAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'panier', 'leclerc_total', 'aldi_total', 'cheapest_supermarket', 'created_at')
    list_filter = ('cheapest_supermarket', 'created_at')
    search_fields = ('user__username', 'panier__id')
    readonly_fields = ('created_at',)
