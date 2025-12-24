from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Panier, Course
from .forms import CourseForm, PanierForm


def landing_page(request):
    return render(request, 'panier/landing.html')


@login_required
def home(request):
    paniers = request.user.paniers.all().order_by('-date_creation')
    for panier in paniers:
        panier.nb_articles = panier.courses.count()
        panier.nom = f"Panier {panier.id}"
    return render(request, "panier/home.html", {"paniers": paniers})


# ========== COURSES ==========

@login_required
def creer_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Course créée avec succès !")
            return redirect('liste_courses')
    else:
        form = CourseForm()
    return render(request, 'panier/creer_course.html', {'form': form})


@login_required
def liste_courses(request):
    """
    Affiche la liste des courses avec gestion du contexte familial ou individuel.

    Pour les utilisateurs avec un nom de famille (last_name) :
    - Affiche toutes les courses présentes dans les paniers de la famille
    - Affiche les courses non associées aux paniers familiaux
    - Liste tous les paniers de la famille pour permettre l'ajout rapide

    Pour les utilisateurs sans nom de famille (utilisateur solo) :
    - Affiche toutes les courses présentes dans ses propres paniers
    - Affiche les courses non associées à ses paniers personnels
    - Liste tous ses paniers personnels pour permettre l'ajout rapide

    Returns:
        render: Template avec courses_par_famille, courses_sans_panier et paniers
    """
    last_name = request.user.last_name

    if last_name:
        # Utilisateur avec famille : contexte familial
        # Courses déjà dans les paniers de la famille (partage familial)
        courses_par_famille = Course.objects.filter(
            paniers__user__last_name__iexact=last_name
        ).distinct()

        # Courses non associées à un panier familial
        courses_sans_panier = Course.objects.exclude(
            paniers__user__last_name__iexact=last_name
        ).distinct()

        # Tous les paniers de la famille (pour le dropdown d'ajout rapide)
        paniers = Panier.objects.filter(user__last_name__iexact=last_name)
    else:
        # Utilisateur sans famille : contexte individuel
        # Courses déjà dans les paniers personnels de l'utilisateur
        courses_par_famille = Course.objects.filter(
            paniers__user=request.user
        ).distinct()

        # Courses non associées aux paniers personnels
        courses_sans_panier = Course.objects.exclude(
            paniers__user=request.user
        ).distinct()

        # Tous les paniers personnels (pour le dropdown d'ajout rapide)
        paniers = Panier.objects.filter(user=request.user)

    return render(request, 'panier/liste_courses.html', {
        'courses_par_famille': courses_par_famille,
        'courses_sans_panier': courses_sans_panier,
        'paniers': paniers
    })


@login_required
def detail_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    # Déterminer le propriétaire
    owner = course.paniers.first().user if course.paniers.exists() else None
    
    # Vérifications d'accès
    is_owner = owner and user == owner
    is_family = owner and (user.last_name.lower() == owner.last_name.lower()) and not is_owner
    is_orphan = not course.paniers.exists()  # Course sans panier

    # Autoriser l'accès aux courses orphelines
    if not (is_owner or is_family or is_orphan):
        return render(request, 'panier/acces_refuse.html',
                      {"message": "Accès refusé : cette course ne vous appartient pas."},
                      status=403)

    ingredients = course.ingredient.splitlines() if course.ingredient else []

    return render(request, 'panier/detail_course.html', {
        'course': course,
        'ingredients': ingredients,
        'owner': owner,
        'can_edit': True,
        'can_delete': is_owner or is_orphan
    })


@login_required
def modifier_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    user_lastname = user.last_name.lower()

    # Autoriser modification des courses orphelines
    is_orphan = not course.paniers.exists()
    is_owner = any(p.user.id == user.id for p in course.paniers.all())
    is_family = any(p.user.last_name.lower() == user_lastname for p in course.paniers.all())
    
    if not (is_owner or is_family or is_orphan):
        return render(request, 'panier/acces_refuse.html',
                      {"message": "Vous n'avez pas le droit de modifier cette course."},
                      status=403)

    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course modifiée avec succès !")
            return redirect('detail_course', course_id=course.id)
    else:
        form = CourseForm(instance=course)

    return render(request, 'panier/modifier_course.html', {'form': form, 'course': course})


@login_required
def supprimer_course(request, course_id):
    """
    Supprime une course.

    Autorisations :
    - Propriétaire (utilisateur qui a créé/ajouté la course en premier) : OUI
    - Membre de la même famille : OUI
    - Courses orphelines (sans panier) : OUI pour tous
    """
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    user_lastname = user.last_name.lower()

    # Déterminer le propriétaire
    owner = course.paniers.first().user if course.paniers.exists() else None

    # Vérifications d'accès
    is_owner = owner and user == owner
    is_family = owner and user_lastname and (user_lastname == owner.last_name.lower()) and not is_owner
    is_orphan = not course.paniers.exists()  # Course sans panier

    if not (is_owner or is_family or is_orphan):
        return render(request, 'panier/acces_refuse.html',
                      {"message": "Vous n'avez pas le droit de supprimer cette course."},
                      status=403)

    if request.method == 'POST':
        course.delete()
        messages.success(request, "Course supprimée avec succès !")
        return redirect('liste_courses')

    return render(request, 'panier/supprimer_course.html', {'course': course})


@login_required
def ajouter_ingredient(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    user = request.user

    owner = course.paniers.first().user if course.paniers.exists() else user
    is_owner = user == owner
    is_family = (user.last_name.lower() == owner.last_name.lower()) and not is_owner
    is_orphan = not course.paniers.exists()

    # Autoriser ajout d'ingrédients aux courses orphelines
    if not (is_owner or is_family or is_orphan):
        return render(request, 'panier/acces_refuse.html',
                      {"message": "Vous n'avez pas le droit d'ajouter un ingrédient à cette course."},
                      status=403)

    if request.method == 'POST':
        new_ingredient = request.POST.get('ingredient')
        if new_ingredient:
            if course.ingredient:
                course.ingredient += f"\n{new_ingredient}"
            else:
                course.ingredient = new_ingredient
            course.save()
            messages.success(request, f"Ingrédient '{new_ingredient}' ajouté !")
            return redirect('detail_course', course_id=course.id)

    return render(request, 'panier/ajouter_ingredient.html', {
        'course': course,
        'owner': owner
    })


@login_required
def supprimer_ingredient(request, course_id, ingredient_index):
    course = get_object_or_404(Course, id=course_id)
    ingredients = course.ingredient.splitlines() if course.ingredient else []

    if 0 <= ingredient_index < len(ingredients):
        suppr = ingredients.pop(ingredient_index)
        course.ingredient = "\n".join(ingredients)
        course.save()
        messages.success(request, f"L'ingrédient '{suppr}' a été supprimé !")
    else:
        messages.error(request, "Ingrédient invalide.")

    return redirect('detail_course', course_id=course.id)


# Ajout rapide d'une course spécifique à un panier
@login_required
def ajouter_course_a_panier(request, course_id, panier_id):
    """
    Ajoute une course spécifique à un panier depuis la liste des courses (ajout rapide).

    Cette vue permet d'ajouter une course à un panier en un clic depuis la liste des courses.
    Les contrôles d'accès vérifient que l'utilisateur a le droit d'ajouter au panier :
    - Pour un utilisateur avec famille : peut ajouter à tous les paniers de la famille
    - Pour un utilisateur solo : peut ajouter uniquement à ses propres paniers

    Args:
        request: La requête HTTP
        course_id: ID de la course à ajouter
        panier_id: ID du panier cible

    Returns:
        redirect: Redirige vers liste_courses avec un message de succès/erreur
    """
    course = get_object_or_404(Course, id=course_id)
    panier = get_object_or_404(Panier, id=panier_id)

    # Vérification des droits d'accès au panier
    user_has_family = bool(request.user.last_name)

    if user_has_family:
        # Utilisateur avec famille : vérifier le partage familial
        is_same_family = panier.user.last_name.lower() == request.user.last_name.lower()
        is_own_basket = panier.user == request.user
        has_access = is_same_family or is_own_basket
    else:
        # Utilisateur sans famille : vérifier la propriété directe
        has_access = panier.user == request.user

    if not has_access:
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_courses')

    # Ajout de la course au panier (si pas déjà présente)
    if course in panier.courses.all():
        messages.info(request, "Cette course est déjà dans ce panier.")
    else:
        panier.courses.add(course)
        messages.success(request, f"Course ajoutée au panier de {panier.user.username} !")

    return redirect('liste_courses')


# ========== PANIERS ==========

@login_required
def creer_panier(request):
    if request.method == 'POST':
        form = PanierForm(request.POST)
        if form.is_valid():
            panier = form.save(commit=False)
            panier.user = request.user
            panier.save()
            # Sauvegarder les courses sélectionnées
            form.save_m2m()
            messages.success(request, "Panier créé avec succès !")
            return redirect('liste_paniers')
    else:
        form = PanierForm()
    return render(request, 'panier/creer_panier.html', {'form': form})


@login_required
def liste_paniers(request):
    last_name = request.user.last_name
    
    if last_name:
        paniers = Panier.objects.filter(
            user__last_name__iexact=last_name
        ).order_by('-date_creation')
    else:
        # Si pas de nom de famille, afficher uniquement les paniers de l'utilisateur
        paniers = Panier.objects.filter(user=request.user).order_by('-date_creation')
    
    return render(request, 'panier/liste_paniers.html', {'paniers': paniers})


@login_required
def detail_panier(request, panier_id):
    panier = get_object_or_404(Panier, id=panier_id)

    # Vérifier accès famille OU utilisateur sans famille
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


# Ajout de courses via formulaire (ajout en masse)
@login_required
def ajouter_course_au_panier(request, panier_id):
    """Affiche un formulaire pour ajouter plusieurs courses à un panier"""
    panier = get_object_or_404(Panier, id=panier_id)
    
    # Vérifier l'accès
    user_has_family = bool(request.user.last_name)
    is_same_family = panier.user.last_name.lower() == request.user.last_name.lower() if user_has_family else False
    is_own_basket = panier.user == request.user
    
    if not (is_same_family or is_own_basket):
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_paniers')
    
    if request.method == 'POST':
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

# # --- Landing page ---
# from django.shortcuts import render

# def landing_page(request):
#     return render(request, 'panier/landing.html')
# from .models import Panier, Course
# # Ajout direct d'une course à un panier
# from django.contrib.auth.decorators import login_required
# @login_required
# def ajouter_une_course_au_panier(request, panier_id, course_id):
#     panier = get_object_or_404(Panier, id=panier_id, user=request.user)
#     course = get_object_or_404(Course, id=course_id)
#     if course in panier.courses.all():
#         messages.info(request, "Cette course est déjà dans le panier.")
#     else:
#         panier.courses.add(course)
#         messages.success(request, "Course ajoutée au panier !")
#     return redirect('detail_panier', panier_id=panier.id)

# from django.shortcuts import render
# from django.contrib.auth.decorators import login_required

# from panier.forms import CourseForm

# from django.shortcuts import render,redirect, get_object_or_404
# from django.contrib import messages

# from panier.models import Course

# # Create your views here.


# @login_required
# def home(request):
#     # Je récupère les paniers de l'utilisateur connecté
#     paniers = request.user.paniers.all().order_by('-date_creation')
#     # Ici, j'ajoute nombre d'articles pour chaque panier
#     for panier in paniers:
#         panier.nb_articles = panier.courses.count()
#         panier.nom = f"Panier {panier.id}"
#     return render(request, "panier/home.html", {"paniers": paniers})

# #courses

# def creer_course(request):
#     if request.method == 'POST':
#         form = CourseForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Course créée avec succès !")
#             return redirect('liste_courses')
#     else:
#         form = CourseForm()
#     return render(request, 'panier/creer_course.html', {'form': form})

# # --- Ajouter un ingrédient à une course ---
# @login_required
# def ajouter_ingredient(request, course_id):
#     course = get_object_or_404(Course, id=course_id)
#     user = request.user

#     owner = course.paniers.first().user if course.paniers.exists() else user

#     is_owner = user == owner
#     is_family = (user.last_name.lower() == owner.last_name.lower()) and not is_owner

#     if not (is_owner or is_family):
#         return render(request, 'panier/acces_refuse.html',
#                       {"message": "Vous n'avez pas le droit d'ajouter un ingrédient à cette course."},
#                       status=403)

#     if request.method == 'POST':
#         new_ingredient = request.POST.get('ingredient')
#         if new_ingredient:
#             if course.ingredient:
#                 course.ingredient += f"\n{new_ingredient}"
#             else:
#                 course.ingredient = new_ingredient
#             course.save()
#             messages.success(request,
#                              f"Ingrédient '{new_ingredient}' ajouté au panier de {owner.username} !")
#             return redirect('detail_course', course_id=course.id)

#     return render(request, 'panier/ajouter_ingredient.html', {
#         'course': course,
#         'owner': owner
#     })

# # --- Liste de toutes les courses ---
# def liste_courses(request):
#     last_name = request.user.last_name

#     # Courses déjà dans les paniers familiaux
#     courses_par_famille = Course.objects.filter(
#         paniers__user__last_name__iexact=last_name
#     ).distinct()

#     # Courses non associées à un panier familial
#     courses_sans_panier = Course.objects.exclude(
#         paniers__user__last_name__iexact=last_name
#     ).distinct()

#     # Paniers uniquement pour cette famille
#     paniers = Panier.objects.filter(user__last_name__iexact=last_name)

#     return render(request, 'panier/liste_courses.html',
#         {
#             'courses_par_famille': courses_par_famille,
#             'courses_sans_panier': courses_sans_panier,
#             'paniers': paniers
#         }
#     )




# # --- Détail d'une course (avec liste des ingrédients) ---
# @login_required
# def detail_course(request, course_id):
#     course = get_object_or_404(Course, id=course_id)
#     user = request.user

#     # Déterminer le propriétaire principal
#     owner = course.paniers.first().user if course.paniers.exists() else user

#     is_owner = user == owner
#     is_family = (user.last_name.lower() == owner.last_name.lower()) and not is_owner

#     # Vérifier accès
#     if not (is_owner or is_family):
#         return render(request, 'panier/acces_refuse.html',
#                       {"message": "Accès refusé : cette course ne vous appartient pas."},
#                       status=403)

#     ingredients = course.ingredient.splitlines() if course.ingredient else []

#     return render(request, 'panier/detail_course.html', {
#         'course': course,
#         'ingredients': ingredients,
#         'owner': owner,
#         'can_edit': True,         
#         'can_delete': is_owner    
#     })




# # --- Modifier une course ---
# def modifier_course(request, course_id):
#     course = get_object_or_404(Course, id=course_id)
#     user = request.user
#     user_lastname = user.last_name.lower()

#     # Vérification permission
#     is_owner = any(p.user.id == user.id for p in course.paniers.all())
#     is_family = any(p.user.last_name.lower() == user_lastname for p in course.paniers.all())
#     if not (is_owner or is_family):
#         return render(
#             request,
#             'panier/acces_refuse.html',
#             {"message": "Vous n'avez pas le droit de modifier cette course."},
#             status=403
#         )

#     if request.method == 'POST':
#         form = CourseForm(request.POST, instance=course)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Course modifiée avec succès !")
#             return redirect('detail_course', course_id=course.id)
#     else:
#         form = CourseForm(instance=course)

#     return render(request, 'panier/modifier_course.html', {'form': form, 'course': course})


# # --- Supprimer une course ---
# def supprimer_course(request, course_id):
#     course = get_object_or_404(Course, id=course_id)
#     user = request.user

#     # Seul le propriétaire peut supprimer
#     is_owner = any(p.user.id == user.id for p in course.paniers.all())
#     if not is_owner:
#         return render(
#             request,
#             'panier/acces_refuse.html',
#             {"message": "Vous n'avez pas le droit de supprimer cette course."},
#             status=403
#         )

#     if request.method == 'POST':
#         course.delete()
#         messages.success(request, "Course supprimée avec succès !")
#         return redirect('liste_courses')

#     return render(request, 'panier/supprimer_course.html', {'course': course})


# # --- Supprimer un ingrédient d'une course ---
# def supprimer_ingredient(request, course_id, ingredient_index):
#     course = get_object_or_404(Course, id=course_id)
#     ingredients = course.ingredient.splitlines() if course.ingredient else []

#     if 0 <= ingredient_index < len(ingredients):
#         suppr = ingredients.pop(ingredient_index)
#         course.ingredient = "\n".join(ingredients)
#         course.save()
#         messages.success(request, f"L'ingrédient '{suppr}' a été supprimé !")
#     else:
#         messages.error(request, "Ingrédient invalide.")

#     return redirect('detail_course', course_id=course.id)

# #paniers
# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib import messages
# from .models import Panier, Course
# from .forms import PanierForm


# # Je crée un nouveau panier
# @login_required
# def creer_panier(request):
#     if request.method == 'POST':
#         form = PanierForm(request.POST)
#         if form.is_valid():
#             panier = form.save(commit=False)
#             panier.user = request.user
#             panier.save()
#             messages.success(request, "Panier créé avec succès !")
#             return redirect('liste_paniers')
#     else:
#         form = PanierForm()
#     return render(request, 'panier/creer_panier.html', {'form': form})


# # J'ajoute des courses à un panier existant
# @login_required
# def ajouter_course_au_panier(request, panier_id):
#     panier = get_object_or_404(Panier, id=panier_id)
#     if request.method == 'POST':
#         form = PanierForm(request.POST, instance=panier)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Courses ajoutées au panier !")
#             return redirect('detail_panier', panier_id=panier.id)
#     else:
#         form = PanierForm(instance=panier)
#     return render(request, 'panier/ajouter_course_au_panier.html', {'form': form, 'panier': panier})


# # J'affiche la liste de tous les paniers
# @login_required
# def liste_paniers(request):
#     #je recupère le nom de famille de l'utilisateur connecté
#     last_name = request.user.last_name 
    
#     #je filtre ensuite les paniers appartenant ayant le même nom de famille
#     if last_name:
#         # Filtrage insensible à la casse et tri décroissant par date
#         paniers = Panier.objects.filter(user__last_name__iexact=last_name).order_by('-date_creation')
#     else:
#         # Aucun panier si pas de nom de famille défini
#         paniers = Panier.objects.none()  
#     return render(request, 'panier/liste_paniers.html', {'paniers': paniers})


# # J'affiche le détail d'un panier
# @login_required
# def detail_panier(request, panier_id):
#     panier = get_object_or_404(Panier, id=panier_id)

#     # Je vérifie que le panier appartient à la même famille
#     if panier.user.last_name.lower() != request.user.last_name.lower():
#         return render(request, 'panier/acces_refuse.html', status=403)

#     return render(request, 'panier/detail_panier.html', {'panier': panier})


# # Je modifie un panier existant
# @login_required
# def modifier_panier(request, panier_id):
#     panier = get_object_or_404(Panier, id=panier_id)
    
#     if panier.user != request.user:
#         messages.error(request, "Vous n'êtes pas autorisé à modifier ce panier.")
#         return redirect('liste_paniers')
    
#     if request.method == 'POST':
#         form = PanierForm(request.POST, instance=panier)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Panier modifié avec succès !")
#             return redirect('detail_panier', panier_id=panier.id)
#     else:
#         form = PanierForm(instance=panier)
#     return render(request, 'panier/modifier_panier.html', {'form': form, 'panier': panier})


# # Je supprime un panier
# @login_required
# def supprimer_panier(request, panier_id):
#     panier = get_object_or_404(Panier, id=panier_id)
    
#     if panier.user != request.user:
#         messages.error(request, "Vous n'êtes pas autorisé à supprimer ce panier.")
#         return redirect('liste_paniers')
    
#     if request.method == 'POST':
#         panier.delete()
#         messages.success(request, "Panier supprimé avec succès !")
#         return redirect('liste_paniers')
#     return render(request, 'panier/supprimer_panier.html', {'panier': panier})



#stripe
import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.urls import reverse



stripe.api_key = settings.STRIPE_SECRET_KEY

# @csrf_exempt
# def create_checkout_session(request):
#     if request.method == "POST":
#         try:
#             checkout_session = stripe.checkout.Session.create(
#                 payment_method_types=['card'],
#                 mode='subscription',
#                 line_items=[{
#                     'price': settings.STRIPE_PRICE_ID,  
#                     'quantity': 1,
#                 }],
#                 success_url="http://localhost:8000/success?session_id={CHECKOUT_SESSION_ID}",
#                 cancel_url="http://localhost:8000/cancel/",
#             )
#             return JsonResponse({'id': checkout_session.id})
#         except Exception as e:
#             return JsonResponse({'error': str(e)})

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


# def success(request):
#     return render(request, "panier/success.html")

def success(request):
    session_id = request.GET.get("session_id")
    if not session_id:
        return render(request, "panier/success.html", {"error": "Session introuvable"})

    # Récupération des infos de la session Stripe
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


#notifications
from django.http import JsonResponse
from django.core import management
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
import os
import time
import logging

logger = logging.getLogger(__name__)


@ratelimit(key='ip', rate='5/h', method=['GET', 'POST'])
@csrf_exempt
@require_http_methods(["GET", "POST"])
def trigger_notification(request):
    """
    Endpoint sécurisé pour déclencher les notifications quotidiennes.
    Appelé par cron-job.org avec un token de sécurité.
    Rate limit: 5 requêtes par heure par IP.
    """
    start_time = time.time()

    # Vérifier si rate limit dépassé
    if getattr(request, 'limited', False):
        logger.warning(f"⚠️ Rate limit dépassé pour IP: {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({
            "error": "Too many requests"
        }, status=429)

    # Log de la requête entrante
    logger.info("=" * 70)
    logger.info(f"🔔 Requête de notification reçue à {timezone.now()}")
    logger.info(f"   User-Agent: {request.META.get('HTTP_USER_AGENT', 'Unknown')}")
    logger.info(f"   IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
    logger.info(f"   Method: {request.method}")

    # Vérification du token de sécurité
    token = request.headers.get("X-CRON-TOKEN")
    expected_token = os.getenv("TOKEN")
    
    if not expected_token:
        logger.error("❌ TOKEN environnement non configuré !")
        return JsonResponse({
            "error": "Server configuration error"
        }, status=500)
    
    if token != expected_token:
        logger.warning(f"⚠️ Tentative d'accès non autorisé")
        logger.warning(f"   Token reçu: {token[:10] if token else 'None'}...")
        logger.warning(f"   IP: {request.META.get('REMOTE_ADDR', 'Unknown')}")
        return JsonResponse({
            "error": "Unauthorized"
        }, status=403)
    
    logger.info("✅ Token validé avec succès")
    
    # Exécution de la commande de notification
    try:
        logger.info("📧 Démarrage de l'envoi des notifications...")
        
        # Exécuter la commande Django
        management.call_command('notify_old_paniers')
        
        elapsed_time = time.time() - start_time
        
        logger.info("✅ Notifications envoyées avec succès")
        logger.info(f"   Temps d'exécution: {elapsed_time:.2f}s")
        logger.info("=" * 70)
        
        return JsonResponse({
            "status": "ok",
            "message": "Notifications sent successfully",
            "execution_time_seconds": round(elapsed_time, 2),
            "timestamp": timezone.now().isoformat()
        }, status=200)
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        
        logger.error("=" * 70)
        logger.error(f"❌ Erreur lors de l'envoi des notifications")
        logger.error(f"   Erreur: {str(e)}")
        logger.error(f"   Temps avant échec: {elapsed_time:.2f}s")
        logger.error("=" * 70)
        logger.exception("Stacktrace complète:")
        
        return JsonResponse({
            "status": "error",
            "message": "Failed to send notifications",
            "error": str(e),
            "execution_time_seconds": round(elapsed_time, 2),
            "timestamp": timezone.now().isoformat()
        }, status=500)


# Endpoint de health check (sans authentification, pour les pings)
@csrf_exempt
@require_http_methods(["GET", "HEAD"])
def health_check(request):
    """
    Endpoint de santé simple pour les monitoring et keep-alive.
    Pas d'authentification requise.
    """
    return JsonResponse({
        "status": "healthy",
        "service": "panier_facile",
        "timestamp": timezone.now().isoformat()
    }, status=200)

# RAG
# from django.http import JsonResponse
# import logging

# logger = logging.getLogger(__name__)

# # Variables globales pour lazy loading du système RAG
# _qa = None
# _vectorstore = None
# _rag_initialized = False

# def initialize_rag_system():
#     """
#     Initialise le système RAG (chargement des documents, embeddings, vectorstore).
#     Cette fonction n'est appelée qu'une seule fois, lors de la première requête.
#     """
#     global _qa, _vectorstore, _rag_initialized
    
#     if _rag_initialized:
#         return _qa, _vectorstore
    
#     try:
#         logger.info("Initialisation du système RAG...")
        
#         # Imports dynamiques pour éviter l'exécution lors des migrations
#         from panier.utils.loader import load_ui_docs
#         from panier.utils.chunker import split_documents
#         from panier.utils.embedding import get_embeddings
#         from panier.utils.vectorstore import build_vectorstore
#         from panier.utils.rag import create_rag
#         from panier.utils.rag_system import rag_system
        
#         # Chargement et traitement des documents
#         documents = load_ui_docs()
#         logger.info(f"{len(documents)} documents chargés")
        
#         # Découpage en chunks
#         chunks = split_documents(documents)
#         logger.info(f"{len(chunks)} chunks créés")
        
#         # Création des embeddings et du vectorstore
#         embeddings = get_embeddings()
#         _vectorstore = build_vectorstore(chunks, embeddings)
#         logger.info("Vectorstore créé")
        
#         # Création de la chaîne RAG
#         _qa = create_rag(_vectorstore)
#         logger.info("Système RAG initialisé avec succès")
        
#         _rag_initialized = True
#         return _qa, _vectorstore
        
#     except Exception as e:
#         logger.error(f"Erreur lors de l'initialisation du système RAG: {str(e)}")
#         raise

# def get_qa_system():
#     """
#     Retourne le système RAG, en l'initialisant si nécessaire.
#     """
#     if not _rag_initialized:
#         return initialize_rag_system()
#     return _qa, _vectorstore

# def chatbot_ui(request):
#     """
#     Vue pour le chatbot UI utilisant le système RAG.
#     Endpoint: GET /chatbot/?question=<ma question>
#     """
#     question = request.GET.get("question", "").strip()
    
#     if not question:
#         return JsonResponse({
#             "answer": "",
#             "error": "Aucune question fournie"
#         }, status=400)
    
#     try:
#         # Import dynamique du retriever
#         from panier.utils.retriever import query_vectorstore
        
#         # Je récupére ou initialise le système RAG
#         qa, vectorstore = get_qa_system()
        
#         # Je récupére les documents pertinents (contexte)
#         context = query_vectorstore(vectorstore, question, k=3)
#         logger.info(f"Question: {question[:100]}...")
        
#         # Je génére la réponse via le RAG
#         prompt = f"Contexte:\n{context}\n\nQuestion: {question}"
#         answer = qa.run(prompt)
        
#         return JsonResponse({
#             "answer": answer,
#             "question": question
#         })
    
#     except Exception as e:
#         logger.error(f"Erreur lors du traitement de la question RAG: {str(e)}", exc_info=True)
        
#         return JsonResponse({
#             "error": "Une erreur est survenue lors du traitement de votre question.",
#             "detail": str(e) if logger.level == logging.DEBUG else None
#         }, status=500)

# def reset_rag_system(request):
#     """
#     Vue pour réinitialiser le système RAG (utile en développement).
#     À protéger avec des permissions appropriées en production.
#     """
#     global _qa, _vectorstore, _rag_initialized
    
#     _qa = None
#     _vectorstore = None
#     _rag_initialized = False
    
#     logger.info("Système RAG réinitialisé")
    
#     return JsonResponse({
#         "status": "success",
#         "message": "Système RAG réinitialisé"
#     })
    
# from django.contrib.admin.views.decorators import staff_member_required

# @staff_member_required
# def reset_rag_system(request):
#     """
#     Vue pour réinitialiser le système RAG (utile en développement).
#     Nécessite d'être connecté en tant que staff member.
#     """
#     global _qa, _vectorstore, _rag_initialized
    
#     _qa = None
#     _vectorstore = None
#     _rag_initialized = False
    
#     logger.info(f"Système RAG réinitialisé par {request.user.username}")
    
#     return JsonResponse({
#         "status": "success",
#         "message": "Système RAG réinitialisé avec succès"
#     })

from django.http import JsonResponse
import logging
from openai import OpenAIError, RateLimitError
from django.contrib.admin.views.decorators import staff_member_required
from .utils import rag_system
from .utils.loader import load_ui_docs
from .utils.chunker import split_documents
from .utils.embedding import get_embeddings
from .utils.vectorstore import build_vectorstore
from .utils.rag import create_rag

logger = logging.getLogger(__name__)

def init_rag_if_needed():
    """J'initialise le RAG seulement si ce n'est pas déjà fait."""
    if rag_system.qa and rag_system.vectorstore:
        return  

    try:
        documents = load_ui_docs()
        logger.info(f"{len(documents)} documents RAG chargés.")

        chunks = split_documents(documents)
        logger.info(f"{len(chunks)} chunks créés.")

        embeddings = get_embeddings()
        vectorstore = build_vectorstore(chunks, embeddings)
        qa = create_rag(vectorstore)

        # Stockage global
        rag_system.qa = qa
        rag_system.vectorstore = vectorstore
        logger.info("Système RAG initialisé à la demande.")

    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation du RAG : {e}", exc_info=True)
        raise e
    
def chatbot_ui(request):
    question = request.GET.get("question", "").strip()
    if not question:
        return JsonResponse({"answer": "", "error": "Aucune question fournie"}, status=400)

    try:
        # J'initialise le RAG si besoin
        init_rag_if_needed()  

        qa = rag_system.qa
        vectorstore = rag_system.vectorstore
        
        if not qa or not vectorstore:
         return JsonResponse({
             "error": "Le chatbot est temporairement indisponible car le quota OpenAI est dépassé ou le système n'a pas pu être initialisé. Veuillez réessayer plus tard."
         }, status=503)


        # Le nouveau système RAG gère la récupération du contexte automatiquement
        logger.info(f"Question: {question[:100]}...")

        try:
            # Utiliser l'API moderne (invoke au lieu de run)
            answer = qa.invoke(question)
        except RateLimitError:
            answer = "Le service est temporairement saturé, veuillez réessayer plus tard."
        except OpenAIError as e:
            answer = f"Erreur OpenAI : {str(e)}"

        return JsonResponse({"answer": answer, "question": question})

    except Exception as e:
        logger.error(f"Erreur RAG : {e}", exc_info=True)
        return JsonResponse({
            "error": "Le système RAG n'a pas pu être initialisé",
            "detail": str(e)
        }, status=500)

# def chatbot_ui(request):
#     question = request.GET.get("question", "").strip()

#     if not question:
#         return JsonResponse({"answer": "", "error": "Aucune question fournie"}, status=400)

#     try:
#         qa = rag_system.qa
#         vectorstore = rag_system.vectorstore

#         if not qa or not vectorstore:
#             return JsonResponse({"error": "Le système RAG n'est pas initialisé"}, status=500)

#         # Récupération du contexte depuis le vectorstore
#         context = query_vectorstore(vectorstore, question, k=3)
#         logger.info(f"Question: {question[:100]}...")

#         prompt = f"Contexte:\n{context}\n\nQuestion: {question}"

#         # Gestion des erreurs OpenAI
#         try:
#             answer = qa.run(prompt)
#         except RateLimitError:
#             answer = "Le service est temporairement saturé, veuillez réessayer plus tard."
#         except OpenAIError as e:
#             answer = f"Erreur OpenAI : {str(e)}"

#         return JsonResponse({"answer": answer, "question": question})

#     except Exception as e:
#         logger.error(f"Erreur RAG : {e}", exc_info=True)
#         return JsonResponse({"error": "Une erreur est survenue.", "detail": str(e)}, status=500)


@staff_member_required
def reset_rag_system(request):
    from .utils import rag_system

    rag_system.qa = None
    rag_system.vectorstore = None

    logger.info(f"Système RAG réinitialisé par {request.user.username}")

    return JsonResponse({
        "status": "success",
        "message": "Système RAG réinitialisé avec succès"
    })