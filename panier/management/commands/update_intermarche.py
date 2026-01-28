"""
Commande Django pour mettre à jour les prix Intermarché manuellement
"""

from django.core.management.base import BaseCommand
from panier.tasks import update_intermarche_prices, update_single_ingredient_price
from panier.models import Ingredient


class Command(BaseCommand):
    help = 'Met à jour les prix Intermarché via scraping'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ingredient-id',
            type=int,
            help='ID d\'un ingrédient spécifique à mettre à jour',
        )
        parser.add_argument(
            '--ingredient-name',
            type=str,
            help='Nom d\'un ingrédient spécifique à mettre à jour',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Exécuter la tâche de manière asynchrone via Celery',
        )

    def handle(self, *args, **options):
        ingredient_id = options.get('ingredient_id')
        ingredient_name = options.get('ingredient_name')
        use_async = options.get('async')

        # Mise à jour d'un ingrédient spécifique
        if ingredient_id or ingredient_name:
            if ingredient_id:
                ing_id = ingredient_id
            else:
                try:
                    ingredient = Ingredient.objects.get(nom__iexact=ingredient_name)
                    ing_id = ingredient.id
                except Ingredient.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"Ingrédient '{ingredient_name}' non trouvé")
                    )
                    return
                except Ingredient.MultipleObjectsReturned:
                    self.stdout.write(
                        self.style.ERROR(f"Plusieurs ingrédients trouvés pour '{ingredient_name}'")
                    )
                    return

            self.stdout.write(f"Mise à jour de l'ingrédient ID={ing_id}...")

            if use_async:
                task = update_single_ingredient_price.delay(ing_id)
                self.stdout.write(
                    self.style.SUCCESS(f"Tâche lancée en arrière-plan (ID: {task.id})")
                )
            else:
                result = update_single_ingredient_price(ing_id)
                if result['status'] == 'success':
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Prix mis à jour: {result['product']['name']} - {result['product'].get('price')}€")
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Erreur: {result.get('message', 'Inconnue')}")
                    )

        # Mise à jour de tous les ingrédients
        else:
            total = Ingredient.objects.count()
            self.stdout.write(f"Mise à jour de {total} ingrédients...")

            if use_async:
                task = update_intermarche_prices.delay()
                self.stdout.write(
                    self.style.SUCCESS(f"Tâche lancée en arrière-plan (ID: {task.id})")
                )
                self.stdout.write("Utilisez 'celery -A config inspect active' pour voir les tâches en cours")
            else:
                self.stdout.write(
                    self.style.WARNING("⚠️  Cela peut prendre plusieurs minutes...")
                )
                result = update_intermarche_prices()

                if result['status'] == 'success':
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"\n✓ Mise à jour terminée:\n"
                            f"  - {result['created']} produits créés\n"
                            f"  - {result['updated']} produits mis à jour\n"
                            f"  - {result['errors']} erreurs"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR("✗ La mise à jour a échoué")
                    )
