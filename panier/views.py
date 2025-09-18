
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from panier.forms import CourseForm

from django.shortcuts import render,redirect, get_object_or_404
from django.contrib import messages

from panier.models import Course

# Create your views here.


@login_required
def home(request):
    # Je récupère les paniers de l'utilisateur connecté
    paniers = request.user.paniers.all().order_by('-date_creation')
    # Ici, j'ajoute nombre d'articles pour chaque panier
    for panier in paniers:
        panier.nb_articles = panier.courses.count()
        panier.nom = f"Panier {panier.id}"
    return render(request, "panier/home.html", {"paniers": paniers})

#courses

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

# --- Ajouter un ingrédient à une course ---
def ajouter_ingredient(request, course_id):
    course = get_object_or_404(Course, id=course_id)

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

    return render(request, 'panier/ajouter_ingredient.html', {'course': course})

# --- Liste de toutes les courses ---
def liste_courses(request):
    courses = Course.objects.all()
    return render(request, 'panier/liste_courses.html', {'courses': courses})

# --- Détail d'une course (avec liste des ingrédients) ---
def detail_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    ingredients = course.ingredient.splitlines() if course.ingredient else []
    return render(request, 'panier/detail_course.html', {'course': course, 'ingredients': ingredients})

# --- Modifier une course ---
def modifier_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Course modifiée avec succès !")
            return redirect('detail_course', course_id=course.id)
    else:
        form = CourseForm(instance=course)

    return render(request, 'panier/modifier_course.html', {'form': form, 'course': course})

# --- Supprimer une course ---
def supprimer_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == 'POST':
        course.delete()
        messages.success(request, "Course supprimée avec succès !")
        return redirect('liste_courses')

    return render(request, 'panier/supprimer_course.html', {'course': course})

# --- Supprimer un ingrédient d'une course ---
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

#paniers
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Panier, Course
from .forms import PanierForm


# Je crée un nouveau panier
@login_required
def creer_panier(request):
    if request.method == 'POST':
        form = PanierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Panier créé avec succès !")
            return redirect('liste_paniers')
    else:
        form = PanierForm()
    return render(request, 'panier/creer_panier.html', {'form': form})


# J'ajoute des courses à un panier existant
@login_required
def ajouter_course_au_panier(request, panier_id):
    panier = get_object_or_404(Panier, id=panier_id)
    if request.method == 'POST':
        form = PanierForm(request.POST, instance=panier)
        if form.is_valid():
            form.save()
            messages.success(request, "Courses ajoutées au panier !")
            return redirect('detail_panier', panier_id=panier.id)
    else:
        form = PanierForm(instance=panier)
    return render(request, 'panier/ajouter_course_au_panier.html', {'form': form, 'panier': panier})


# J'affiche la liste de tous les paniers
@login_required
def liste_paniers(request):
    paniers = Panier.objects.all()
    return render(request, 'panier/liste_paniers.html', {'paniers': paniers})


# J'affiche le détail d'un panier
@login_required
def detail_panier(request, panier_id):
    panier = get_object_or_404(Panier, id=panier_id)
    return render(request, 'panier/detail_panier.html', {'panier': panier})


# Je modifie un panier existant
@login_required
def modifier_panier(request, panier_id):
    panier = get_object_or_404(Panier, id=panier_id)
    if request.method == 'POST':
        form = PanierForm(request.POST, instance=panier)
        if form.is_valid():
            form.save()
            messages.success(request, "Panier modifié avec succès !")
            return redirect('detail_panier', panier_id=panier.id)
    else:
        form = PanierForm(instance=panier)
    return render(request, 'panier/modifier_panier.html', {'form': form, 'panier': panier})


# Je supprime un panier
@login_required
def supprimer_panier(request, panier_id):
    panier = get_object_or_404(Panier, id=panier_id)
    if request.method == 'POST':
        panier.delete()
        messages.success(request, "Panier supprimé avec succès !")
        return redirect('liste_paniers')
    return render(request, 'panier/supprimer_panier.html', {'panier': panier})