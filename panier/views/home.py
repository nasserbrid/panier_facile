"""
Vues pour les pages d'accueil.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def landing_page(request):
    from contact.models import CustomerReview

    top_reviews = CustomerReview.objects.filter(is_approved=True).order_by('-is_featured', '-rating', '-created_at')[:3]

    return render(request, 'pages/landing.html', {
        'top_reviews': top_reviews
    })


@login_required
def home(request):
    paniers = request.user.paniers.all().order_by('-date_creation')
    for panier in paniers:
        panier.nb_articles = panier.courses.count()
        panier.nom = f"Panier {panier.id}"
    return render(request, "pages/home.html", {"paniers": paniers})
