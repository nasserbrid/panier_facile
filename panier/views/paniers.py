"""
Vues pour la gestion des paniers.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django_ratelimit.decorators import ratelimit

from ..models import Panier, Course
from ..forms import PanierForm


@login_required
def ajouter_course_a_panier(request, course_id, panier_id):
    """
    Ajoute une course spécifique à un panier depuis la liste des courses (ajout rapide).
    """
    course = get_object_or_404(Course, id=course_id)
    panier = get_object_or_404(Panier, id=panier_id)

    user_has_family = bool(request.user.last_name)

    if user_has_family:
        is_same_family = panier.user.last_name.lower() == request.user.last_name.lower()
        is_own_basket = panier.user == request.user
        has_access = is_same_family or is_own_basket
    else:
        has_access = panier.user == request.user

    if not has_access:
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_courses')

    if course in panier.courses.all():
        messages.info(request, "Cette course est déjà dans ce panier.")
    else:
        panier.courses.add(course)
        messages.success(request, f"Course ajoutée au panier de {panier.user.username} !")

    return redirect('liste_courses')


@login_required
@ratelimit(key='user', rate='50/h', method='POST')
def creer_panier(request):
    """
    Créer un nouveau panier.
    Rate limit: 50 créations par heure par utilisateur.
    """
    if request.method == 'POST':
        if getattr(request, 'limited', False):
            messages.error(request, 'Trop de paniers créés. Veuillez patienter quelques instants.')
            return redirect('liste_paniers')

        form = PanierForm(request.POST)
        if form.is_valid():
            panier = form.save(commit=False)
            panier.user = request.user
            panier.save()
            form.save_m2m()
            messages.success(request, "Panier créé avec succès !")
            return redirect('liste_paniers')
    else:
        form = PanierForm()

        last_name = request.user.last_name
        if last_name:
            form.fields['courses'].queryset = Course.objects.filter(
                created_by__last_name__iexact=last_name
            )
        else:
            form.fields['courses'].queryset = Course.objects.filter(
                created_by=request.user
            )

    return render(request, 'panier/creer_panier.html', {'form': form})


@login_required
def liste_paniers(request):
    last_name = request.user.last_name

    if last_name:
        paniers = Panier.objects.filter(
            user__last_name__iexact=last_name
        ).order_by('-date_creation')
    else:
        paniers = Panier.objects.filter(user=request.user).order_by('-date_creation')

    return render(request, 'panier/liste_paniers.html', {'paniers': paniers})


@login_required
def detail_panier(request, panier_id):
    panier = get_object_or_404(Panier, id=panier_id)

    user_has_family = bool(request.user.last_name)
    is_same_family = panier.user.last_name.lower() == request.user.last_name.lower() if user_has_family else False
    is_own_basket = panier.user == request.user

    if not (is_same_family or is_own_basket):
        return render(request, 'panier/acces_refuse.html', status=403)

    return render(request, 'panier/detail_panier.html', {'panier': panier})


@login_required
def modifier_panier(request, panier_id):
    panier = get_object_or_404(Panier, id=panier_id)

    if panier.user != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à modifier ce panier.")
        return redirect('liste_paniers')

    if request.method == 'POST':
        form = PanierForm(request.POST, instance=panier)
        if form.is_valid():
            form.save()
            messages.success(request, "Panier modifié avec succès !")
            return redirect('detail_panier', panier_id=panier.id)
    else:
        form = PanierForm(instance=panier)

    return render(request, 'panier/modifier_panier.html', {'form': form, 'panier': panier})


@login_required
def supprimer_panier(request, panier_id):
    panier = get_object_or_404(Panier, id=panier_id)

    if panier.user != request.user:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer ce panier.")
        return redirect('liste_paniers')

    if request.method == 'POST':
        panier.delete()
        messages.success(request, "Panier supprimé avec succès !")
        return redirect('liste_paniers')

    return render(request, 'panier/supprimer_panier.html', {'panier': panier})


@login_required
@ratelimit(key='user', rate='50/h', method='POST')
def ajouter_course_au_panier(request, panier_id):
    """
    Affiche un formulaire pour ajouter plusieurs courses à un panier.
    Rate limit: 50 ajouts par heure par utilisateur.
    """
    panier = get_object_or_404(Panier, id=panier_id)

    user_has_family = bool(request.user.last_name)
    is_same_family = panier.user.last_name.lower() == request.user.last_name.lower() if user_has_family else False
    is_own_basket = panier.user == request.user

    if not (is_same_family or is_own_basket):
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_paniers')

    if request.method == 'POST':
        if getattr(request, 'limited', False):
            messages.error(request, 'Trop d\'ajouts de courses. Veuillez patienter quelques instants.')
            return redirect('detail_panier', panier_id=panier.id)

        form = PanierForm(request.POST, instance=panier)
        if form.is_valid():
            form.save()
            messages.success(request, "Courses ajoutées au panier !")
            return redirect('detail_panier', panier_id=panier.id)
    else:
        form = PanierForm(instance=panier)

    return render(request, 'panier/ajouter_course_au_panier.html', {
        'form': form,
        'panier': panier
    })
