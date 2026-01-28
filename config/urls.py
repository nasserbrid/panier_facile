"""
URL configuration for PanierFacile project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView
import authentication.views
import panier.views
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Landing page
    path('', panier.views.landing_page, name='landing'),

    # Auth routes
    path('login/', LoginView.as_view(
        template_name='authentication/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', authentication.views.CustomLogoutView.as_view(), name='logout'),
    path('signup/', authentication.views.signup_page, name='signup'),

    # Django allauth (Google OAuth)
    path('accounts/', include('allauth.urls')),

    # Auth reset / password
    path('auth/', include('authentication.urls')),

    # Toutes les routes panier (courses, paniers, stripe)
    path('panier/', include('panier.urls')),

    # Route home directe pour faciliter l'accès
    path('home/', panier.views.home, name='home'),

    # Pages légales (depuis core.views)
    path('mentions-legales/', core_views.mentions_legales, name='mentions_legales'),
    path('rgpd/', core_views.rgpd, name='rgpd'),
    path('cgu/', core_views.cgu, name='cgu'),
]
