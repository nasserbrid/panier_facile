from django.urls import path
from . import views
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView, PasswordChangeDoneView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    path('signup/', views.signup_page, name='signup'),
    path('profile/', views.profile_page, name='profile'),
    path('api/save-location/', views.save_location, name='save_location'),
    path('nearby-stores/', views.nearby_stores, name='nearby_stores'),
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

    # Gestion d'abonnement
    path('subscription/status/', views.subscription_status, name='subscription_status'),
    path('subscription/upgrade/', views.subscription_upgrade, name='subscription_upgrade'),
    path('subscription/create-checkout/', views.create_subscription_checkout, name='create_subscription_checkout'),
    path('subscription/success/', views.subscription_success, name='subscription_success'),
    path('subscription/webhook/', views.stripe_subscription_webhook, name='stripe_subscription_webhook'),

]
