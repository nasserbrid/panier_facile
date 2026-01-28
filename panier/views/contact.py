"""
Vues pour le contact et les avis clients.
"""
import logging
from django.shortcuts import render, redirect
from django.contrib import messages
from django_ratelimit.decorators import ratelimit

logger = logging.getLogger(__name__)


@ratelimit(key='ip', rate='5/h', method='POST')
def contact(request):
    """
    Affiche et traite le formulaire de contact.
    Rate limit: 5 soumissions par heure par IP pour éviter le spam.
    """
    from ..contact_forms import ContactForm
    from contact.models import ContactMessage
    from django.core.mail import send_mail
    from django.conf import settings

    if request.method == 'POST':
        if getattr(request, 'limited', False):
            messages.error(request, 'Trop de messages envoyés. Veuillez réessayer dans quelques instants.')
            return redirect('contact')

        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message_text = form.cleaned_data['message']

            ContactMessage.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message_text
            )

            try:
                admin_email = settings.EMAIL_HOST_USER
                email_subject = f"[Contact PanierFacile] {subject}"
                email_body = f"""
Nouveau message de contact reçu via PanierFacile

Nom: {name}
Email: {email}
Sujet: {subject}

Message:
{message_text}

---
Ce message a été envoyé depuis le formulaire de contact de PanierFacile.
Vous pouvez répondre directement à l'adresse: {email}
                """

                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_email],
                    fail_silently=False,
                )

                logger.info(f"Email de contact envoyé de {email} vers {admin_email}")
                messages.success(request, "Votre message a été envoyé avec succès ! Nous vous répondrons dans les plus brefs délais.")
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi de l'email de contact: {e}")
                messages.warning(request, "Votre message a été enregistré, mais l'email de notification n'a pas pu être envoyé.")

            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'contact/contact.html', {'form': form})


def submit_review(request):
    """Affiche et traite le formulaire d'avis client"""
    from ..contact_forms import ReviewForm
    from contact.models import CustomerReview

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            CustomerReview.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                rating=form.cleaned_data['rating'],
                title=form.cleaned_data['title'],
                review=form.cleaned_data['review'],
                would_recommend=form.cleaned_data['would_recommend']
            )
            messages.success(request, "Merci pour votre avis ! Il sera publié après validation.")
            return redirect('submit_review')
    else:
        form = ReviewForm()

    return render(request, 'contact/submit_review.html', {'form': form})


def reviews_list(request):
    """Affiche la liste des avis clients approuves"""
    from contact.models import CustomerReview

    reviews = CustomerReview.objects.filter(is_approved=True).order_by('-created_at')

    return render(request, 'contact/reviews_list.html', {'reviews': reviews})
