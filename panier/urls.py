# from django.urls import path
# from . import views

# urlpatterns = [
#     path('creer_course/', views.creer_course, name='creer_course'),
#     path('creer_panier/', views.creer_panier, name='creer_panier'),
#     path('courses/', views.liste_courses, name='liste_courses'),
#     path('courses/<int:course_id>/', views.detail_course, name='detail_course'),
#     path('courses/<int:course_id>/ajouter_ingredient/', views.ajouter_ingredient, name='ajouter_ingredient'),
#     path('courses/<int:course_id>/modifier/', views.modifier_course, name='modifier_course'),
#     path('courses/<int:course_id>/supprimer/', views.supprimer_course, name='supprimer_course'),
#     path('<int:panier_id>/', views.detail_panier, name='detail_panier'),
#     path('<int:panier_id>/ajouter_course/', views.ajouter_course_au_panier, name='ajouter_course_au_panier'),
#     path('', views.liste_paniers, name='liste_paniers'),
#     path('<int:panier_id>/modifier/', views.modifier_panier, name='modifier_panier'),
#     path('<int:panier_id>/supprimer/', views.supprimer_panier, name='supprimer_panier'),
#     path('home/', views.home, name='home'),
#     # Ajout direct d'une course à un panier
#     path('<int:panier_id>/ajouter_course/<int:course_id>/', views.ajouter_une_course_au_panier, name='ajouter_une_course_au_panier'),
#     path("create-checkout-session/", views.create_checkout_session, name="create_checkout_session"),
#     path("success/", views.success, name="success"),
#     path("cancel/", views.cancel, name="cancel"),
# ]
from django.urls import path
from . import views

urlpatterns = [
    # Page d'accueil des paniers
    # path('', views.landing_page, name='landing'),
    path('', views.liste_paniers, name='liste_paniers'),
    path('home/', views.home, name='panier_home'),  
    
    # Gestion des courses
    path('creer_course/', views.creer_course, name='creer_course'),
    path('courses/', views.liste_courses, name='liste_courses'),
    path('courses/<int:course_id>/', views.detail_course, name='detail_course'),
    path('courses/<int:course_id>/ajouter_ingredient/', views.ajouter_ingredient, name='ajouter_ingredient'),
    path('courses/<int:course_id>/modifier/', views.modifier_course, name='modifier_course'),
    path('courses/<int:course_id>/supprimer/', views.supprimer_course, name='supprimer_course'),
    
    path('courses/<int:course_id>/ajouter-au-panier/<int:panier_id>/', views.ajouter_course_a_panier, name='ajouter_course_a_panier'),
    
    # Gestion des paniers
    path('creer_panier/', views.creer_panier, name='creer_panier'),
    path('<int:panier_id>/', views.detail_panier, name='detail_panier'),
    path('<int:panier_id>/ajouter_course/', views.ajouter_course_au_panier, name='ajouter_course_au_panier'),
    path('<int:panier_id>/modifier/', views.modifier_panier, name='modifier_panier'),
    path('<int:panier_id>/supprimer/', views.supprimer_panier, name='supprimer_panier'),
    
    path('paniers/<int:panier_id>/ajouter-courses/', views.ajouter_course_au_panier, name='ajouter_course_au_panier'),
    
    # Ajout direct d'une course à un panier
    path('<int:panier_id>/ajouter_course/<int:course_id>/', views.ajouter_course_au_panier, name='ajouter_course_au_panier'),
    
    # Stripe
    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('success/', views.success, name='success'),
    path('cancel/', views.cancel, name='cancel'),
    
    #notifications
    path('trigger-notification/', views.trigger_notification, name='trigger_notification'),
    path('health', views.health_check, name='health'),
    
    #RAG - Chatbot UI
   # Chatbot RAG
    path('chatbot/', views.chatbot_ui, name='chatbot_ui'),
    
    # Gestion du système RAG (réservé au staff)
    path('chatbot/reset/', views.reset_rag_system, name='reset_rag'),
]