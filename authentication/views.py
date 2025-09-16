from django.shortcuts import render, redirect
from authentication.forms import SignupForm
from django.contrib.auth import login
from django.conf import settings
from django.contrib.auth.views import LogoutView

# Create your views here.

class CustomLogoutView(LogoutView):
    next_page = 'login'
    

def signup_page(request):
    
    form = SignupForm()
    
    if request.method == 'POST':
        form = SignupForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    
    return render(request, "authentication/signup.html", context={"form": form})