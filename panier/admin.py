from django.contrib import admin
from .models import Course, Panier, Ingredient, IngredientPanier


# Enregistrer les modeles core
admin.site.register(Course)
admin.site.register(Panier)
admin.site.register(Ingredient)
admin.site.register(IngredientPanier)
