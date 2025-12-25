from django.shortcuts import render, redirect
from authentication.forms import SignupForm
from django.contrib.auth import login
from django.conf import settings
from django.contrib.auth.views import LogoutView
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django_ratelimit.decorators import ratelimit
import json
import stripe
from authentication.utils import OverpassAPI

stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.


"""
Vue pour la déconnexion personnalisée d'un utilisateur.
    
    Hérite de Django LogoutView et redirige vers la page de connexion
    après la déconnexion.
"""
class CustomLogoutView(LogoutView):
    next_page = 'login'
    

def signup_page(request):
    """
    Vue pour la page d'inscription d'un nouvel utilisateur.
    
    Cette vue gère l'affichage du formulaire d'inscription et la création
    de l'utilisateur lorsque le formulaire est soumis.

    Si le formulaire est valide, l'utilisateur est créé, connecté et redirigé
    vers la page définie par LOGIN_REDIRECT_URL dans settings.
"""
    
    form = SignupForm()
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    
    return render(request, "authentication/signup.html", context={"form": form})


@login_required
def profile_page(request):
    """
    Vue pour la page de profil utilisateur avec géolocalisation.

    Affiche le profil de l'utilisateur connecté avec la possibilité
    de définir sa localisation (GPS ou adresse manuelle).
    """
    user = request.user

    # Récupérer les coordonnées existantes si disponibles
    location_data = None
    if user.location:
        location_data = {
            'latitude': user.location.y,
            'longitude': user.location.x,
            'address': user.address or ''
        }

    return render(request, "authentication/profile.html", {
        'user': user,
        'location_data': location_data
    })


@ratelimit(key='user', rate='10/m', method='POST')
@login_required
@require_http_methods(["POST"])
def save_location(request):
    """
    API endpoint pour sauvegarder la localisation de l'utilisateur.

    Accepte soit:
    - latitude et longitude (géolocalisation GPS)
    - address (adresse à géocoder)

    Retourne un JSON avec le statut de l'opération.
    Rate limit: 10 requêtes par minute par utilisateur.
    """
    # Vérifier si rate limit dépassé
    if getattr(request, 'limited', False):
        return JsonResponse({
            'success': False,
            'message': 'Trop de requêtes. Veuillez réessayer dans quelques instants.'
        }, status=429)

    try:
        data = json.loads(request.body)
        user = request.user

        latitude = data.get('latitude')
        longitude = data.get('longitude')
        address = data.get('address', '')

        if latitude and longitude:
            # Validation des coordonnées GPS
            try:
                lat = float(latitude)
                lon = float(longitude)
            except (TypeError, ValueError):
                return JsonResponse({
                    'success': False,
                    'message': 'Coordonnées GPS invalides'
                }, status=400)

            if not (-90 <= lat <= 90):
                return JsonResponse({
                    'success': False,
                    'message': 'Latitude doit être entre -90 et 90'
                }, status=400)

            if not (-180 <= lon <= 180):
                return JsonResponse({
                    'success': False,
                    'message': 'Longitude doit être entre -180 et 180'
                }, status=400)
            # Importer Point uniquement si GeoDjango est disponible
            try:
                from django.contrib.gis.geos import Point
                user.location = Point(float(longitude), float(latitude), srid=4326)
                user.address = address
                user.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Localisation enregistrée avec succès',
                    'latitude': latitude,
                    'longitude': longitude
                })
            except ImportError:
                return JsonResponse({
                    'success': False,
                    'message': 'GeoDjango n\'est pas disponible (mode développement local)'
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'message': 'Latitude et longitude requises'
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Format JSON invalide'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur: {str(e)}'
        }, status=500)


@login_required
def nearby_stores(request):
    """
    Vue pour afficher les commerces à proximité de l'utilisateur.

    Nécessite que l'utilisateur ait défini sa localisation.
    """
    user = request.user

    if not user.location:
        return render(request, "authentication/nearby_stores.html", {
            'error': 'Vous devez d\'abord définir votre localisation dans votre profil.'
        })

    # Récupérer les paramètres de recherche
    radius = int(request.GET.get('radius', 2000))  # Par défaut 2km
    shop_type_filter = request.GET.get('type', 'all')

    # Types de commerces à rechercher
    shop_types = None
    if shop_type_filter != 'all':
        shop_types = [shop_type_filter]

    # Récupérer les commerces via Overpass API
    latitude = user.location.y
    longitude = user.location.x

    stores = OverpassAPI.find_nearby_stores(
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        shop_types=shop_types
    )

    # Statistiques
    stats = {
        'total': len(stores),
        'by_type': {}
    }
    for store in stores:
        store_type = store['type']
        stats['by_type'][store_type] = stats['by_type'].get(store_type, 0) + 1

    return render(request, "authentication/nearby_stores.html", {
        'stores': stores,
        'stats': stats,
        'user_location': {
            'latitude': latitude,
            'longitude': longitude,
            'address': user.address
        },
        'radius': radius,
        'shop_types': OverpassAPI.SHOP_TYPES,
        'selected_type': shop_type_filter
    })


# ========================================
# VUES DE GESTION D'ABONNEMENT
# TEMPORAIREMENT DÉSACTIVÉ - À réactiver après migration
# ========================================

"""
@login_required
def subscription_status(request):
    '''
    Affiche le statut d'abonnement de l'utilisateur.
    '''
    user = request.user
    context = {
        'user': user,
        'has_active_subscription': user.has_active_subscription,
        'days_remaining': user.days_remaining,
        'subscription_status': user.subscription_status,
        'trial_end_date': user.trial_end_date,
    }
    return render(request, 'authentication/subscription_status.html', context)


@login_required
def subscription_upgrade(request):
    '''
    Page d'upgrade pour les utilisateurs dont l'abonnement a expiré.
    '''
    user = request.user
    context = {
        'user': user,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }
    return render(request, 'authentication/subscription_upgrade.html', context)


@csrf_exempt
def create_subscription_checkout(request):
    '''
    Crée une session Stripe Checkout pour l'abonnement à 1€/mois.
    '''
    if request.method == "POST":
        try:
            user = request.user

            success_url = request.build_absolute_uri(
                reverse("subscription_success")
            ) + "?session_id={CHECKOUT_SESSION_ID}"

            cancel_url = request.build_absolute_uri(reverse("subscription_upgrade"))

            # Créer ou récupérer le customer Stripe
            if user.stripe_customer_id:
                customer_id = user.stripe_customer_id
            else:
                customer = stripe.Customer.create(
                    email=user.email,
                    metadata={
                        'user_id': user.id,
                        'username': user.username,
                    }
                )
                customer_id = customer.id
                user.stripe_customer_id = customer_id
                user.save(update_fields=['stripe_customer_id'])

            # Créer la session de paiement
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                mode='subscription',
                line_items=[{
                    'price': settings.STRIPE_PRICE_ID,  # L'ID du prix à 1€/mois
                    'quantity': 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': user.id,
                }
            )

            return JsonResponse({'id': checkout_session.id})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def subscription_success(request):
    '''
    Page de confirmation après un paiement réussi.
    Met à jour le statut d'abonnement de l'utilisateur.
    '''
    session_id = request.GET.get("session_id")
    if not session_id:
        return render(request, "authentication/subscription_success.html", {
            "error": "Session introuvable"
        })

    try:
        # Récupérer les infos de la session Stripe
        session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["customer", "subscription"]
        )

        user = request.user

        # Mettre à jour l'utilisateur avec les infos Stripe
        user.stripe_customer_id = session.customer.id if hasattr(session.customer, 'id') else session.customer
        user.stripe_subscription_id = session.subscription.id if hasattr(session.subscription, 'id') else session.subscription
        user.subscription_status = 'active'
        user.save(update_fields=['stripe_customer_id', 'stripe_subscription_id', 'subscription_status'])

        context = {
            "customer_email": session.customer_email or user.email,
            "subscription_id": user.stripe_subscription_id,
            "amount_total": session.amount_total / 100 if session.amount_total else 1.00,
        }

        return render(request, "authentication/subscription_success.html", context)

    except Exception as e:
        return render(request, "authentication/subscription_success.html", {
            "error": f"Erreur lors de la récupération de la session: {str(e)}"
        })


@csrf_exempt
def stripe_subscription_webhook(request):
    '''
    Webhook pour gérer les événements Stripe (renouvellement, annulation, etc.).
    '''
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    # Gérer les différents types d'événements
    if event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    elif event['type'] == 'invoice.payment_succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])

    return JsonResponse({'status': 'success'})


def handle_subscription_updated(subscription):
    '''
    Gère la mise à jour d'un abonnement.
    '''
    from authentication.models import User

    try:
        user = User.objects.get(stripe_subscription_id=subscription['id'])

        # Mettre à jour le statut selon le status Stripe
        if subscription['status'] == 'active':
            user.subscription_status = 'active'
        elif subscription['status'] in ['canceled', 'unpaid']:
            user.subscription_status = 'canceled'

        user.save(update_fields=['subscription_status'])
    except User.DoesNotExist:
        pass


def handle_subscription_deleted(subscription):
    '''
    Gère l'annulation d'un abonnement.
    '''
    from authentication.models import User

    try:
        user = User.objects.get(stripe_subscription_id=subscription['id'])
        user.subscription_status = 'canceled'
        user.save(update_fields=['subscription_status'])
    except User.DoesNotExist:
        pass


def handle_payment_succeeded(invoice):
    '''
    Gère le succès d'un paiement.
    '''
    from authentication.models import User

    try:
        subscription_id = invoice.get('subscription')
        if subscription_id:
            user = User.objects.get(stripe_subscription_id=subscription_id)
            user.subscription_status = 'active'
            user.save(update_fields=['subscription_status'])
    except User.DoesNotExist:
        pass


def handle_payment_failed(invoice):
    '''
    Gère l'échec d'un paiement.
    '''
    from authentication.models import User

    try:
        subscription_id = invoice.get('subscription')
        if subscription_id:
            user = User.objects.get(stripe_subscription_id=subscription_id)
            user.subscription_status = 'expired'
            user.save(update_fields=['subscription_status'])
    except User.DoesNotExist:
        pass
"""