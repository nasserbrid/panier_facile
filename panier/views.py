# --- Landing page ---
from django.shortcuts import render
def landing_page(request):
    return render(request, 'panier/landing.html')
from .models import Panier, Course
# Ajout direct d'une course à un panier
from django.contrib.auth.decorators import login_required
@login_required
def ajouter_une_course_au_panier(request, panier_id, course_id):
    panier = get_object_or_404(Panier, id=panier_id, user=request.user)
    course = get_object_or_404(Course, id=course_id)
    if course in panier.courses.all():
        messages.info(request, "Cette course est déjà dans le panier.")
    else:
        panier.courses.add(course)
        messages.success(request, "Course ajoutée au panier !")
    return redirect('detail_panier', panier_id=panier.id)

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
    last_name = request.user.last_name

    # On ne montre que les courses liées aux paniers des membres de la même famille
    courses = Course.objects.filter(paniers__user__last_name__iexact=last_name).distinct()
    paniers = Panier.objects.filter(user__last_name__iexact=last_name)

    return render(request, 'panier/liste_courses.html', {'courses': courses, 'paniers': paniers})


# --- Détail d'une course (avec liste des ingrédients) ---
def detail_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if course.panier.user.last_name.lower() != request.user.last_name.lower():
        return render(request, 'panier/acces_refuse.html', status=403)

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
    #je recupère le nom de famille de l'utilisateur connecté
    last_name = request.user.last_name 
    
    #je filtre ensuite les paniers appartenant ayant le même nom de famille
    if last_name:
        # Filtrage insensible à la casse et tri décroissant par date
        paniers = Panier.objects.filter(user__last_name=last_name).order_by('-date_creation')
    else:
        # Aucun panier si pas de nom de famille défini
        paniers = Panier.objects.none()  
    return render(request, 'panier/liste_paniers.html', {'paniers': paniers})


# J'affiche le détail d'un panier
@login_required
def detail_panier(request, panier_id):
    panier = get_object_or_404(Panier, id=panier_id)

    # Je vérifie que le panier appartient à la même famille
    if panier.user.last_name.lower() != request.user.last_name.lower():
        return render(request, 'panier/acces_refuse.html', status=403)

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
    amount_total = session.amount_total / 100  # en euros

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
import os

def trigger_notification(request):
    token = request.headers.get("X-CRON-TOKEN")
    if token != os.getenv("TOKEN"):
        return JsonResponse({"error": "Unauthorized"}, status=403)
    management.call_command('notify_old_paniers')
    return JsonResponse({"status": "ok"})

