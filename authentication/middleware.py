# TEMPORAIREMENT DÉSACTIVÉ - À réactiver après migration
"""
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


class SubscriptionMiddleware:

    Middleware qui vérifie si l'utilisateur a un abonnement actif.
    Redirige vers la page d'upgrade si l'abonnement a expiré.


    # URLs exemptées de la vérification d'abonnement
    EXEMPT_URLS = [
        '/login/',
        '/logout/',
        '/signup/',
        '/admin/',
        '/static/',
        '/media/',
        '/subscription/upgrade/',
        '/subscription/status/',
        '/create-checkout-session/',
        '/success/',
        '/cancel/',
        '/webhook/',
        '/',  # Page d'accueil/landing
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifier si l'utilisateur est authentifié
        if request.user.is_authenticated:
            # Vérifier si l'URL est exemptée
            if not self._is_exempt_url(request.path):
                # Vérifier si l'utilisateur a un abonnement actif
                if not request.user.has_active_subscription:
                    # Mettre à jour le statut si la période d'essai est expirée
                    if request.user.subscription_status == 'trial':
                        request.user.subscription_status = 'expired'
                        request.user.save(update_fields=['subscription_status'])

                    # Rediriger vers la page d'upgrade
                    return redirect('subscription_upgrade')

        response = self.get_response(request)
        return response

    def _is_exempt_url(self, path):

        Vérifie si l'URL est exemptée de la vérification d'abonnement.

        for exempt_url in self.EXEMPT_URLS:
            if path.startswith(exempt_url):
                return True
        return False
"""
#Middleware qui vérifie que l'utilisateur a un numéro de téléphone renseigné.
#Redirige vers la page de profil si le numéro de téléphone est manquant.
from django.shortcuts import redirect


class PhoneNumberMiddleware:
    
     # URLs exemptées de la vérification d'abonnement
    EXEMPT_URLS = [
        '/login/',
        '/logout/',
        '/signup/',
        '/admin/',
        '/static/',
        '/profile/complete/',
        '/media/',
        '/',
    ]
    

    #Laisse passer les requêtes non authentifiées (pas de user connecté -> pas de redirection)
    def __init__(self, get_response):
        self.get_response = get_response
        
    
    def __call__(self, request):
        # Vérifier si l'utilisateur est authentifié
        if request.user.is_authenticated:
            # Vérifier si l'URL est exemptée
            if not self._is_exempt_url(request.path):
                # Vérifier si l'utilisateur a un numéro de téléphone renseigné
                if not request.user.phone_number:
                    # Rediriger vers la page de profil
                    return redirect('complete_profile')      

        response = self.get_response(request)
        return response
    
    def _is_exempt_url(self, path):

        """Vérifie si l'URL est exemptée de la vérification du numéro de téléphone."""

        for exempt_url in self.EXEMPT_URLS:
            if path.startswith(exempt_url):
                return True
        return False
