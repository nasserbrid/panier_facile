from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

urlpatterns = [
    path('login/', LoginView.as_view(
        template_name='authentication/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('signup/', views.signup_page, name='signup'),
    path('change-password/', PasswordChangeView.as_view(
        template_name="authentication/password_change_form.html"), name='password_change'),
    path('password_reset/', PasswordResetView.as_view(
        template_name="authentication/password_reset_form.html"), name="password_reset"),
    path('password_reset/done/', PasswordResetDoneView.as_view(
        template_name="authentication/password_reset_done.html"), name="password_reset_done"),
    path('reset/<uidb64>/<token>/', PasswordResetConfirmView.as_view(
        template_name="authentication/password_reset_confirm.html"), name="password_reset_confirm"),
    path('reset/done/', PasswordResetCompleteView.as_view(
        template_name="authentication/password_reset_complete.html"),
         name="password_reset_complete"),
    
]
