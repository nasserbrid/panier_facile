"""
URL configuration for core project.

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
from django.views.generic import RedirectView
from django.contrib import admin
from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

import authentication.views
import panier.views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', LoginView.as_view(
        template_name= 'authentication/login.html',
        redirect_authenticated_user = True
    ), name='login'),
      path('logout/', authentication.views.CustomLogoutView.as_view(), name='logout'),
    path('change-password/', PasswordChangeView.as_view(
        template_name = "authentication/password_change_form.html"), name='password_change'),
    #path('change-password-done/', PasswordChangeDoneView.as_view(template_name = "authentication/password_change_done.html"), name='password_change_done'),
    path('password_reset/done/', PasswordResetDoneView.as_view(
        template_name="authentication/password_reset_done.html"), name="password_reset_done"),
    #path('password_reset/', PasswordResetView.as_view(), name="password_reset"),
    path('password_reset/', PasswordResetView.as_view(
        template_name="authentication/password_reset_form.html"), name="password_reset"),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
        template_name="authentication/password_reset_confirm.html"), name="password_reset_confirm"),
    path('reset/done/', PasswordResetCompleteView.as_view(
        template_name="authentication/password_reset_complete.html"), name="password_reset_complete"),
    path('signup/', authentication.views.signup_page, name='signup'),
    
    path('creer_course/', panier.views.creer_course, name='creer_course'),
    path('creer_panier/', panier.views.creer_panier, name='creer_panier'),
    path('courses/', panier.views.liste_courses, name='liste_courses'),
    path('courses/<int:course_id>/', panier.views.detail_course, name='detail_course'),
    path('courses/<int:course_id>/ajouter_ingredient/', panier.views.ajouter_ingredient, name='ajouter_ingredient'),
    path('courses/<int:course_id>/modifier/', panier.views.modifier_course, name='modifier_course'),
    path('home/', panier.views.home, name='home'),
    path('panier/', panier.views.liste_paniers, name='panier'),
    path('', RedirectView.as_view(url='/home/'), name='index'),
   
    
    
]
