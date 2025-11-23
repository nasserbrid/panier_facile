from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from panier.models import Panier
from django.contrib.auth import get_user_model
from datetime import timedelta
from django.conf import settings

class Command(BaseCommand):
    help = "Envoie une notification aux utilisateurs pour les paniers créés il y a 2 semaines."

    def handle(self, *args, **options):
        User = get_user_model()
        deux_semaines = timezone.now() - timedelta(days=14)
        # On ne prend que la date (pas l'heure) pour matcher la journée
        date_cible = deux_semaines.date()
        utilisateurs = User.objects.all()
        for user in utilisateurs:
            # paniers = Panier.objects.filter(user=user, date_creation__date=date_cible)
            
            #prise en compte des paniers plus anciens au cas où l'email n'a pas été envoyé le jour même (≤ il y a 14 jours, donc paniers âgés de 14 jours ou plus)
            paniers = Panier.objects.filter(user=user,date_creation__date__lte=date_cible)
            
            if paniers.exists():
                for panier in paniers:
                    courses = panier.courses.all()
                    liste_courses = "\n".join([f"- {c.titre}" for c in courses])
                    message = (
                        f"Bonjour {user.username},\n\n"
                        f"Vous devez faire vos courses car cela fait deux semaines depuis votre dernier panier.\n"
                        f"Voici la liste des courses de ce panier :\n{liste_courses if liste_courses else 'Aucune course.'}\n\n"
                        f"À bientôt sur PanierFacile !"
                    )
                    send_mail(
                        subject="Rappel : Il est temps de refaire vos courses !",
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Notification envoyée à {user.email}"))
            else:
                self.stdout.write(f"Aucun panier à notifier pour {user.username}")
