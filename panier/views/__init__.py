"""
Package de vues pour l'application panier.

Ce fichier maintient la compatibilité avec les imports existants
en réexportant toutes les vues depuis leurs modules respectifs.
"""

# Home
from .home import landing_page, home
from .courses import (
    creer_course,
    liste_courses,
    detail_course,
    modifier_course,
    supprimer_course,
    ajouter_ingredient,
    supprimer_ingredient,
)
from .paniers import (
    ajouter_course_a_panier,
    creer_panier,
    liste_paniers,
    detail_panier,
    modifier_panier,
    supprimer_panier,
    ajouter_course_au_panier,
)

# Stripe
from .stripe import (
    create_checkout_session,
    success,
    cancel,
)
# Contact et avis
from .contact import (
    contact,
    submit_review,
    reviews_list,
)
# Géolocalisation
from .drive import save_temp_location

# Comparaison de prix
from .price_comparison import (
    compare_prices,
    comparison_progress,
    comparison_results,
    comparison_status_api,
)

# Chatbot
from .chatbot import (
    chatbot_ui,
    reset_rag_system,
)
# Health et notifications
from .health import (
    trigger_notification,
    health_check,
)

__all__ = [
    # Home
    'landing_page',
    'home',
    # Courses
    'creer_course',
    'liste_courses',
    'detail_course',
    'modifier_course',
    'supprimer_course',
    'ajouter_ingredient',
    'supprimer_ingredient',
    # Paniers
    'ajouter_course_a_panier',
    'creer_panier',
    'liste_paniers',
    'detail_panier',
    'modifier_panier',
    'supprimer_panier',
    'ajouter_course_au_panier',
    # Stripe
    'create_checkout_session',
    'success',
    'cancel',
    # Notifications
    'trigger_notification',
    # Health
    'health_check',
    # Chatbot
    'chatbot_ui',
    'reset_rag_system',
    # Géolocalisation
    'save_temp_location',
    # Comparaison de prix
    'compare_prices',
    'comparison_progress',
    'comparison_results',
    'comparison_status_api',
    # Contact
    'contact',
    'submit_review',
    'reviews_list',
]
