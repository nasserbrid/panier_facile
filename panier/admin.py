from django.contrib import admin
from .models import (
    Course, Panier, Ingredient, IngredientPanier,
    IntermarcheProductMatch, IntermarcheCart,
    ContactMessage, CustomerReview
)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_read', 'is_replied')
    list_filter = ('is_read', 'is_replied', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Informations du contact', {
            'fields': ('name', 'email', 'subject', 'message')
        }),
        ('Statut', {
            'fields': ('is_read', 'is_replied', 'created_at')
        }),
    )


@admin.register(CustomerReview)
class CustomerReviewAdmin(admin.ModelAdmin):
    list_display = ('get_author', 'rating', 'title', 'created_at', 'is_approved', 'is_featured', 'would_recommend')
    list_filter = ('rating', 'is_approved', 'is_featured', 'would_recommend', 'created_at')
    search_fields = ('name', 'email', 'title', 'review')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    list_editable = ('is_approved', 'is_featured')

    fieldsets = (
        ('Informations du client', {
            'fields': ('name', 'email')
        }),
        ('Avis', {
            'fields': ('rating', 'title', 'review', 'would_recommend')
        }),
        ('Modération', {
            'fields': ('is_approved', 'is_featured', 'created_at')
        }),
    )

    def get_author(self, obj):
        return obj.name if obj.name else 'Anonyme'
    get_author.short_description = 'Auteur'


# Enregistrer les autres modèles sans configuration personnalisée
admin.site.register(Course)
admin.site.register(Panier)
admin.site.register(Ingredient)
admin.site.register(IngredientPanier)
admin.site.register(IntermarcheProductMatch)
admin.site.register(IntermarcheCart)
