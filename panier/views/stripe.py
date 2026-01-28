"""
Vues pour l'intégration Stripe (paiements/abonnements).
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


@csrf_exempt
def create_checkout_session(request):
    if request.method == "POST":
        try:
            success_url = request.build_absolute_uri(
                reverse("success")
            ) + "?session_id={CHECKOUT_SESSION_ID}"

            cancel_url = request.build_absolute_uri(reverse("cancel"))

            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                mode='subscription',
                line_items=[{
                    'price': settings.STRIPE_PRICE_ID,
                    'quantity': 1,
                }],
                success_url=success_url,
                cancel_url=cancel_url,
            )
            return JsonResponse({'id': checkout_session.id})
        except Exception as e:
            return JsonResponse({'error': str(e)})


def success(request):
    session_id = request.GET.get("session_id")
    if not session_id:
        return render(request, "panier/success.html", {"error": "Session introuvable"})

    session = stripe.checkout.Session.retrieve(session_id, expand=["customer", "subscription"])

    customer_email = session.customer_email
    subscription_id = session.subscription
    amount_total = session.amount_total / 100

    context = {
        "customer_email": customer_email,
        "subscription_id": subscription_id,
        "amount_total": amount_total,
    }
    return render(request, "panier/success.html", context)


def cancel(request):
    return render(request, "panier/cancel.html")
