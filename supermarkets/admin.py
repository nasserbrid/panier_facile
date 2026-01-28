"""
Administration Django pour les modèles supermarkets.
"""
from django.contrib import admin
from .models import CarrefourProductMatch, AuchanProductMatch, PriceComparison


@admin.register(CarrefourProductMatch)
class CarrefourProductMatchAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'product_name', 'price', 'store_id', 'is_available', 'last_updated')
    list_filter = ('is_available', 'store_id')
    search_fields = ('ingredient__nom', 'product_name')
    readonly_fields = ('created_at', 'last_updated')


@admin.register(AuchanProductMatch)
class AuchanProductMatchAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'product_name', 'price', 'store_id', 'is_available', 'last_updated')
    list_filter = ('is_available', 'store_id')
    search_fields = ('ingredient__nom', 'product_name')
    readonly_fields = ('created_at', 'last_updated')


@admin.register(PriceComparison)
class PriceComparisonAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'panier', 'carrefour_total', 'auchan_total', 'cheapest_supermarket', 'created_at')
    list_filter = ('cheapest_supermarket', 'created_at')
    search_fields = ('user__username', 'panier__id')
    readonly_fields = ('created_at',)
