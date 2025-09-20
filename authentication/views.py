from django.shortcuts import render, redirect
from authentication.forms import SignupForm
from django.contrib.auth import login
from django.conf import settings
from django.contrib.auth.views import LogoutView

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