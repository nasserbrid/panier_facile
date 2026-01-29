"""
Signaux Django pour l'application panier.

Ce module contient les signaux pour le Cache Proactif:
- Déclenche le scraping des prix quand une Course est créée/modifiée
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender='panier.Course')
def trigger_ingredient_scraping(sender, instance, created, **kwargs):
    """
    Signal déclenché après la sauvegarde d'une Course.

    Lance le scraping proactif des ingrédients pour pré-remplir le cache
    avant que l'utilisateur ne demande la comparaison de prix.

    Args:
        instance: L'objet Course sauvegardé
        created: True si création, False si modification
    """
    # Import lazy pour éviter les imports circulaires
    from .tasks import scrape_ingredient_prices

    # Vérifier que la course a des ingrédients
    if not instance.ingredient or not instance.ingredient.strip():
        logger.debug(f"Course {instance.id} sans ingrédient, skip scraping")
        return

    # Parser les ingrédients (un par ligne)
    ingredient_lines = [
        line.strip()
        for line in instance.ingredient.split('\n')
        if line.strip()
    ]

    if not ingredient_lines:
        return

    action = "créée" if created else "modifiée"
    logger.info(
        f"[Cache Proactif] Course {instance.id} {action}, "
        f"lancement scraping pour {len(ingredient_lines)} ingrédients"
    )

    # Lancer la tâche Celery en background (haute priorité)
    try:
        scrape_ingredient_prices.delay(ingredient_lines, priority='high')
    except Exception as e:
        # Ne pas bloquer la sauvegarde si Celery n'est pas disponible
        logger.error(f"[Cache Proactif] Erreur lancement scraping: {e}")
