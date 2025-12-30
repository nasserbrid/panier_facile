from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .models import Panier, Course, Ingredient, IngredientPanier
from .forms import CourseForm, PanierForm


def landing_page(request):
    from .models import CustomerReview

    # Ici, je récupère les 3 meilleurs avis (featured ou les mieux notés)
    top_reviews = CustomerReview.objects.filter(is_approved=True).order_by('-is_featured', '-rating', '-created_at')[:3]

    return render(request, 'panier/landing.html', {
        'top_reviews': top_reviews
    })


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
            # Ici, je crée la course sans la sauvegarder encore
            course = form.save(commit=False)
            # Ici, j'assigne l'utilisateur connecté comme créateur
            course.created_by = request.user
            # Ici, je sauvegarde la course avec le créateur
            course.save()
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
    - Affiche les courses créées par la famille non encore dans un panier
    - Liste tous les paniers de la famille pour permettre l'ajout rapide

    Pour les utilisateurs sans nom de famille (utilisateur solo) :
    - Affiche toutes les courses présentes dans ses propres paniers
    - Affiche les courses créées par lui non encore dans un panier
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

        # Ici, je récupère uniquement les courses créées par la famille ET non dans un panier familial
        courses_sans_panier = Course.objects.filter(
            created_by__last_name__iexact=last_name
        ).exclude(
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

        # Ici, je récupère uniquement les courses créées par l'utilisateur ET non dans ses paniers
        courses_sans_panier = Course.objects.filter(
            created_by=request.user
        ).exclude(
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
    - Propriétaire (utilisateur dont le panier contient la course) : OUI
    - Membre de la même famille : OUI
    - Autres utilisateurs : NON
    """
    try:
        course = get_object_or_404(Course, id=course_id)
        user = request.user

        # Ici, je vérifie si la course est associée à des paniers
        if not course.paniers.exists():
            # Ici, la course est orpheline (non associée à un panier)
            # Seuls le créateur ou les membres de la famille du créateur peuvent la supprimer

            last_name = user.last_name
            can_delete_orphan = False

            # Ici, je vérifie si l'utilisateur est le créateur de la course
            if course.created_by == user:
                can_delete_orphan = True
            # Sinon, je vérifie si l'utilisateur est de la même famille que le créateur
            elif last_name and course.created_by.last_name:
                if last_name.lower() == course.created_by.last_name.lower():
                    can_delete_orphan = True

            if not can_delete_orphan:
                return render(request, 'panier/access_refuse.html',
                              {"message": "Vous n'avez pas le droit de supprimer cette course."},
                              status=403)

            if request.method == 'POST':
                course.delete()
                messages.success(request, "Course supprimée avec succès !")
                return redirect('liste_courses')

            return render(request, 'panier/supprimer_course.html', {
                'course': course,
                'can_delete': True
            })

        # Ici, la course est associée à au moins un panier
        # Je détermine le propriétaire (utilisateur du premier panier associé)
        panier = course.paniers.first()
        if not panier:
            return render(request, 'panier/access_refuse.html',
                          {"message": "Cette course n'est associée à aucun panier valide."},
                          status=403)

        owner = panier.user
        if not owner:
            return render(request, 'panier/access_refuse.html',
                          {"message": "Le panier associé n'a pas de propriétaire."},
                          status=403)

        # Ici, je vérifie les autorisations d'accès
        is_owner = user == owner

        # Ici, je vérifie si l'utilisateur est de la même famille (gestion des valeurs None/vides pour last_name)
        is_family = False
        if not is_owner and user.last_name and owner.last_name:
            user_lastname = user.last_name.lower()
            owner_lastname = owner.last_name.lower()
            is_family = user_lastname == owner_lastname

        # Ici, je refuse l'accès si l'utilisateur n'est ni propriétaire ni membre de la famille
        if not (is_owner or is_family):
            return render(request, 'panier/access_refuse.html',
                          {"message": "Vous n'avez pas le droit de supprimer cette course."},
                          status=403)

        if request.method == 'POST':
            course.delete()
            messages.success(request, "Course supprimée avec succès !")
            return redirect('liste_courses')

        return render(request, 'panier/supprimer_course.html', {
            'course': course,
            'can_delete': True
        })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur dans supprimer_course pour course_id={course_id}: {str(e)}", exc_info=True)
        return render(request, 'panier/access_refuse.html',
                      {"message": f"Une erreur est survenue lors de la suppression de la course: {str(e)}"},
                      status=500)


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

        # Ici, je filtre les courses selon la logique familiale
        last_name = request.user.last_name
        if last_name:
            # Ici, l'utilisateur a un nom de famille
            # Il voit uniquement les courses créées par sa famille
            form.fields['courses'].queryset = Course.objects.filter(
                created_by__last_name__iexact=last_name
            )
        else:
            # Ici, l'utilisateur n'a pas de nom de famille (utilisateur principal)
            # Il voit uniquement les courses qu'il a créées
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


# ========== INTÉGRATION INTERMARCHÉ ==========

from panier.models import IntermarcheCart
from panier.intermarche_api import IntermarcheAPIClient, IntermarcheAPIException
from panier.services.product_matcher import ProductMatcher
from authentication.utils import OverpassAPI
import uuid


@login_required
def export_to_intermarche(request, panier_id):
    """
    Étape 1: Sélection du magasin Intermarché pour exporter le panier.

    Cette vue affiche les magasins Intermarché proches de l'utilisateur
    et permet de sélectionner un magasin pour l'export du panier.

    Flow:
    1. Vérifier que l'utilisateur a une localisation GPS
    2. Récupérer les magasins proches via l'API Intermarché
    3. Afficher la liste des magasins avec carte
    4. Rediriger vers intermarche_match_products avec le store_id
    """
    panier = get_object_or_404(Panier, id=panier_id)

    # Vérifier l'accès au panier
    user_has_family = bool(request.user.last_name)
    is_same_family = panier.user.last_name.lower() == request.user.last_name.lower() if user_has_family else False
    is_own_basket = panier.user == request.user

    if not (is_same_family or is_own_basket):
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_paniers')

    # Vérifier que l'utilisateur a une localisation GPS
    if not request.user.location:
        return render(request, 'panier/intermarche_no_location.html', {
            'panier': panier
        })

    try:
        # Récupérer les magasins proches
        api_client = IntermarcheAPIClient()
        stores = api_client.find_stores_near_location(
            latitude=request.user.location.y,
            longitude=request.user.location.x,
            distance=10000,  # 10km
            limit=10
        )

        if not stores:
            messages.warning(request, "Aucun magasin Intermarché trouvé à proximité (10km).")
            return redirect('detail_panier', panier_id=panier.id)

        # Calculer les distances et préparer les données pour le template
        for store in stores:
            store_lat = store.get('latitude')
            store_lon = store.get('longitude')
            if store_lat and store_lon:
                distance_m = OverpassAPI._calculate_distance(
                    request.user.location.y,
                    request.user.location.x,
                    store_lat,
                    store_lon
                )
                store['distance_km'] = round(distance_m / 1000, 1)
            else:
                store['distance_km'] = None

        # Trier par distance
        stores = sorted([s for s in stores if s.get('distance_km') is not None],
                       key=lambda x: x['distance_km'])

        return render(request, 'panier/intermarche_select_store.html', {
            'panier': panier,
            'stores': stores,
            'user_location': {
                'lat': request.user.location.y,
                'lon': request.user.location.x
            }
        })

    except IntermarcheAPIException as e:
        logger.error(f"Erreur API Intermarché: {e.message}")
        messages.error(request, "Impossible de récupérer la liste des magasins Intermarché.")
        return redirect('detail_panier', panier_id=panier.id)


@login_required
def intermarche_match_products(request, panier_id):
    """
    Étape 2: Validation des correspondances produits.

    Cette vue affiche les correspondances trouvées entre les ingrédients
    du panier et les produits Intermarché, et permet de les valider/modifier.

    Flow:
    1. Récupérer le store_id depuis GET
    2. Matcher tous les ingrédients du panier
    3. Afficher les matches avec possibilité de modification
    4. POST: Valider et rediriger vers intermarche_create_cart
    """
    panier = get_object_or_404(Panier, id=panier_id)

    # Vérifier l'accès au panier
    user_has_family = bool(request.user.last_name)
    is_same_family = panier.user.last_name.lower() == request.user.last_name.lower() if user_has_family else False
    is_own_basket = panier.user == request.user

    if not (is_same_family or is_own_basket):
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_paniers')

    store_id = request.GET.get('store_id') or request.POST.get('store_id')
    if not store_id:
        messages.error(request, "Aucun magasin sélectionné.")
        return redirect('export_to_intermarche', panier_id=panier.id)

    # Récupérer les ingrédients du panier depuis les courses
    # Le système utilise Course.ingredient (TextField) et non IngredientPanier
    courses_with_ingredients = []
    for course in panier.courses.all():
        if course.ingredient and course.ingredient.strip():
            courses_with_ingredients.append(course)

    if not courses_with_ingredients:
        logger.warning(f"Panier {panier_id} ne contient aucun ingrédient")
        messages.warning(request, "Ce panier ne contient aucun ingrédient. Veuillez d'abord ajouter des ingrédients.")
        return redirect('detail_panier', panier_id=panier.id)

    # Convertir les courses en objets Ingredient et IngredientPanier
    # pour que le ProductMatcher puisse fonctionner
    ingredient_paniers = []
    for course in courses_with_ingredients:
        # Parser les ingrédients (séparés par \n)
        ingredient_lines = [line.strip() for line in course.ingredient.split('\n') if line.strip()]

        for ingredient_text in ingredient_lines:
            # Créer ou récupérer l'objet Ingredient
            ingredient, _ = Ingredient.objects.get_or_create(
                nom=ingredient_text,
                defaults={'quantite': '1', 'unite': ''}
            )

            # Créer ou récupérer l'IngredientPanier
            ing_panier, _ = IngredientPanier.objects.get_or_create(
                panier=panier,
                ingredient=ingredient,
                defaults={'quantite': 1}
            )
            ingredient_paniers.append(ing_panier)

    logger.info(f"Panier {panier_id} contient {len(ingredient_paniers)} ingrédients")

    # Lancer la tâche Celery asynchrone pour le matching
    from .tasks import match_panier_with_intermarche

    logger.info(f"🚀 Lancement de la tâche Celery pour matcher le panier {panier_id}")
    task = match_panier_with_intermarche.delay(panier_id, store_id)

    # Stocker le task_id dans la session pour le suivi
    request.session[f'matching_task_{panier_id}'] = task.id

    # Rediriger vers la page de progression
    messages.info(
        request,
        f"Préparation de votre panier en cours... ({len(ingredient_paniers)} produits à chercher)"
    )
    return redirect('intermarche_matching_progress', panier_id=panier.id, store_id=store_id)


@login_required
def intermarche_matching_progress(request, panier_id, store_id):
    """
    Page de progression du matching asynchrone avec Intermarché

    Cette vue affiche la progression en temps réel du scraping Celery
    et redirige automatiquement vers les résultats une fois terminé.

    Args:
        panier_id: ID du panier
        store_id: ID du magasin Intermarché
    """
    from celery.result import AsyncResult

    panier = get_object_or_404(Panier, id=panier_id)

    # Vérifier l'accès au panier
    user_has_family = bool(request.user.last_name)
    is_same_family = panier.user.last_name.lower() == request.user.last_name.lower() if user_has_family else False
    is_own_basket = panier.user == request.user

    if not (is_same_family or is_own_basket):
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_paniers')

    # Récupérer le task_id depuis la session
    task_id = request.session.get(f'matching_task_{panier_id}')

    if not task_id:
        # Pas de tâche en cours, rediriger vers la sélection du magasin
        messages.warning(request, "Aucune recherche de produits en cours.")
        return redirect('select_store_for_drive', panier_id=panier.id)

    # Récupérer le statut de la tâche Celery
    task_result = AsyncResult(task_id)

    context = {
        'panier': panier,
        'store_id': store_id,
        'task_id': task_id,
        'task_status': task_result.state,  # PENDING, STARTED, SUCCESS, FAILURE
    }

    # Si la tâche est terminée avec succès, récupérer les résultats
    if task_result.ready():
        if task_result.successful():
            result_data = task_result.result
            context['result'] = result_data
            context['matched_count'] = result_data.get('matched', 0)
            context['total_count'] = result_data.get('total', 0)
            context['success_rate'] = result_data.get('success_rate', 0)

            # Nettoyer le task_id de la session
            if f'matching_task_{panier_id}' in request.session:
                del request.session[f'matching_task_{panier_id}']

        else:
            # La tâche a échoué
            context['error'] = str(task_result.info)
            messages.error(request, "Une erreur est survenue lors de la recherche des produits.")

    return render(request, 'panier/intermarche_matching_progress.html', context)


@login_required
def intermarche_create_cart(request, panier_id):
    """
    Étape 3: Création du panier Intermarché et redirection.

    Cette vue crée le panier sur Intermarché Drive via l'API
    et redirige l'utilisateur vers le site Intermarché.

    Flow:
    1. Récupérer les matches validés
    2. Créer le panier via l'API Carts
    3. Enregistrer IntermarcheCart en DB
    4. Rediriger vers le site Intermarché Drive
    """
    panier = get_object_or_404(Panier, id=panier_id)

    # Vérifier l'accès au panier
    user_has_family = bool(request.user.last_name)
    is_same_family = panier.user.last_name.lower() == request.user.last_name.lower() if user_has_family else False
    is_own_basket = panier.user == request.user

    if not (is_same_family or is_own_basket):
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_paniers')

    store_id = request.GET.get('store_id')
    if not store_id:
        messages.error(request, "Aucun magasin sélectionné.")
        return redirect('export_to_intermarche', panier_id=panier.id)

    try:
        # Récupérer les ingrédients du panier
        ingredient_paniers = list(panier.ingredient_paniers.all())

        if not ingredient_paniers:
            messages.error(request, "Ce panier ne contient aucun ingrédient.")
            return redirect('detail_panier', panier_id=panier.id)

        # Matcher les produits
        matcher = ProductMatcher(store_id)
        matches = matcher.match_panier_ingredients(ingredient_paniers)

        # Convertir en items pour l'API
        items = matcher.get_cart_items_from_matches(matches, ingredient_paniers)

        if not items:
            messages.error(request, "Aucun produit trouvé. Impossible de créer le panier Intermarché.")
            return redirect('detail_panier', panier_id=panier.id)

        # Créer le panier via l'API Intermarché
        api_client = IntermarcheAPIClient()
        anonymous_id = str(uuid.uuid4())

        logger.info(f"Création panier Intermarché pour panier {panier.id}, magasin {store_id}")
        cart_response = api_client.create_cart(
            store_id=store_id,
            items=items,
            anonymous_id=anonymous_id
        )

        # Enregistrer le panier Intermarché en DB
        intermarche_cart = IntermarcheCart.objects.create(
            user=request.user,
            panier=panier,
            store_id=store_id,
            store_name=cart_response.get('storeName', ''),
            anonymous_cart_id=anonymous_id,
            total_amount=cart_response.get('totalAmount', 0),
            items_count=len(items),
            status='sent',
            sync_response=cart_response
        )

        logger.info(f"Panier Intermarché créé: {intermarche_cart.id}")

        # Rediriger vers Intermarché Drive
        redirect_url = intermarche_cart.intermarche_url

        messages.success(request, f"Panier créé avec succès! {len(items)} produits ajoutés.")

        return render(request, 'panier/intermarche_redirect.html', {
            'panier': panier,
            'intermarche_cart': intermarche_cart,
            'redirect_url': redirect_url,
            'items_count': len(items)
        })

    except IntermarcheAPIException as e:
        logger.error(f"Erreur API Intermarché: {e.message}")

        # Enregistrer l'échec en DB
        IntermarcheCart.objects.create(
            user=request.user,
            panier=panier,
            store_id=store_id,
            anonymous_cart_id=str(uuid.uuid4()),
            status='failed',
            error_message=e.message
        )

        return render(request, 'panier/intermarche_error.html', {
            'panier': panier,
            'error_message': e.message
        })
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        messages.error(request, "Une erreur inattendue s'est produite.")
        return redirect('detail_panier', panier_id=panier.id)


# ========== CONTACT ET AVIS ==========

def contact(request):
    """Affiche et traite le formulaire de contact"""
    from .contact_forms import ContactForm
    from .models import ContactMessage

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Ici, je sauvegarde le message de contact en base de données
            ContactMessage.objects.create(
                name=form.cleaned_data['name'],
                email=form.cleaned_data['email'],
                subject=form.cleaned_data['subject'],
                message=form.cleaned_data['message']
            )
            messages.success(request, "Votre message a été envoyé avec succès ! Nous vous répondrons dans les plus brefs délais.")
            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'panier/contact.html', {'form': form})


def submit_review(request):
    """Affiche et traite le formulaire d'avis client"""
    from .contact_forms import ReviewForm
    from .models import CustomerReview

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            # Ici, je sauvegarde l'avis client en base de données
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

    return render(request, 'panier/submit_review.html', {'form': form})


@login_required
def select_store_for_drive(request, panier_id):
    """
    Page de sélection de magasin avec géolocalisation intégrée.
    Permet à l'utilisateur de:
    - Se géolocaliser directement depuis cette page
    - Voir les magasins Intermarché à proximité
    - Voir les autres commerces à proximité
    - Choisir un magasin pour son drive
    """
    panier = get_object_or_404(Panier, id=panier_id)

    # Vérifier l'accès au panier
    user_has_family = bool(request.user.last_name)
    is_same_family = panier.user.last_name.lower() == request.user.last_name.lower() if user_has_family and panier.user.last_name else False
    is_own_basket = panier.user == request.user

    if not (is_same_family or is_own_basket):
        messages.error(request, "Vous n'avez pas accès à ce panier.")
        return redirect('liste_paniers')

    # Vérifier que le panier contient des courses avec des ingrédients
    courses_count = panier.courses.count()
    has_ingredients = False

    for course in panier.courses.all():
        # Le champ ingredient est un TextField contenant du texte
        if course.ingredient and course.ingredient.strip():
            has_ingredients = True
            break

    if courses_count == 0 or not has_ingredients:
        messages.warning(request, "Ce panier ne contient aucun ingrédient. Veuillez d'abord ajouter des ingrédients aux courses avant de créer un drive.")
        return redirect('detail_panier', panier_id=panier.id)

    # Récupérer la localisation actuelle (session temporaire en priorité, sinon profil)
    user_location = None

    # 1. Vérifier la localisation temporaire en session (prioritaire)
    if 'temp_location' in request.session:
        temp_loc = request.session['temp_location']
        user_location = {
            'latitude': temp_loc['latitude'],
            'longitude': temp_loc['longitude'],
            'address': temp_loc.get('address', '')
        }
    # 2. Sinon, utiliser la localisation du profil
    elif request.user.location:
        user_location = {
            'latitude': request.user.location.y,
            'longitude': request.user.location.x,
            'address': request.user.address or ''
        }

    # Récupérer les magasins si une localisation est disponible
    stores = []
    nearby_stores = []

    if user_location:
        try:
            from authentication.utils import OverpassAPI

            overpass = OverpassAPI()

            # Recherche optimisée des magasins Intermarché
            stores = overpass.find_intermarche_stores(
                latitude=user_location['latitude'],
                longitude=user_location['longitude'],
                radius=5000  # 5km
            )

            # Recherche des autres commerces (optionnel)
            try:
                all_stores = overpass.find_nearby_stores(
                    latitude=user_location['latitude'],
                    longitude=user_location['longitude'],
                    radius=2000,  # 2km seulement pour les autres
                    shop_types=['supermarket', 'convenience']  # Limiter aux types principaux
                )
                # Exclure les Intermarché déjà trouvés
                nearby_stores = [s for s in all_stores
                                if 'intermarché' not in s.get('name', '').lower()
                                and 'intermarche' not in s.get('name', '').lower()][:10]
            except Exception:
                # Si la recherche des autres commerces échoue, continuer quand même
                nearby_stores = []

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des magasins: {e}")
            messages.warning(request, "Impossible de récupérer les magasins à proximité pour le moment.")

    context = {
        'panier': panier,
        'user_location': user_location,
        'intermarche_stores': stores,
        'nearby_stores': nearby_stores,
    }

    return render(request, 'panier/select_store_for_drive.html', context)


@login_required
@require_http_methods(["POST"])
def save_temp_location(request):
    """
    Sauvegarde temporairement la localisation de l'utilisateur.
    Peut être utilisé pour stocker la localisation sans mettre à jour le profil.
    """
    import json
    from django.contrib.gis.geos import Point

    try:
        data = json.loads(request.body)
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        address = data.get('address', '')

        # Option 1: Sauvegarder dans le profil utilisateur
        if data.get('save_to_profile', False):
            request.user.location = Point(longitude, latitude, srid=4326)
            request.user.address = address
            request.user.save()

        # Option 2: Sauvegarder en session (temporaire)
        request.session['temp_location'] = {
            'latitude': latitude,
            'longitude': longitude,
            'address': address
        }

        return JsonResponse({
            'success': True,
            'message': 'Localisation enregistrée avec succès'
        })

    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def reviews_list(request):
    """Affiche la liste des avis clients approuvés"""
    from .models import CustomerReview

    # Ici, je récupère uniquement les avis approuvés
    reviews = CustomerReview.objects.filter(is_approved=True).order_by('-created_at')

    return render(request, 'panier/reviews_list.html', {'reviews': reviews})