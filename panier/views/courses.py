"""
Vues pour la gestion des courses (recettes).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ..models import Panier, Course
from ..forms import CourseForm


@login_required
def creer_course(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.created_by = request.user
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
    """
    last_name = request.user.last_name

    if last_name:
        courses_par_famille = Course.objects.filter(
            paniers__user__last_name__iexact=last_name
        ).distinct()

        courses_sans_panier = Course.objects.filter(
            created_by__last_name__iexact=last_name
        ).exclude(
            paniers__user__last_name__iexact=last_name
        ).distinct()

        paniers = Panier.objects.filter(user__last_name__iexact=last_name)
    else:
        courses_par_famille = Course.objects.filter(
            paniers__user=request.user
        ).distinct()

        courses_sans_panier = Course.objects.filter(
            created_by=request.user
        ).exclude(
            paniers__user=request.user
        ).distinct()

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

    owner = course.paniers.first().user if course.paniers.exists() else None

    is_owner = owner and user == owner
    is_family = owner and (user.last_name.lower() == owner.last_name.lower()) and not is_owner
    is_orphan = not course.paniers.exists()

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
    """
    try:
        course = get_object_or_404(Course, id=course_id)
        user = request.user

        if not course.paniers.exists():
            last_name = user.last_name
            can_delete_orphan = False

            if course.created_by == user:
                can_delete_orphan = True
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

        is_owner = user == owner

        is_family = False
        if not is_owner and user.last_name and owner.last_name:
            user_lastname = user.last_name.lower()
            owner_lastname = owner.last_name.lower()
            is_family = user_lastname == owner_lastname

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
