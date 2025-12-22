"""
Commande Django pour initialiser les tâches périodiques Celery Beat.

Usage:
    python manage.py setup_periodic_tasks
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule


class Command(BaseCommand):
    help = 'Configure les tâches périodiques Celery Beat pour les notifications'

    def handle(self, *args, **options):
        self.stdout.write('Configuration des tâches périodiques Celery Beat...')

        # Créer les horaires (8h00 et 18h00)
        schedule_8h, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='8',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='Europe/Paris'
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Horaire 8h00 créé'))
        else:
            self.stdout.write('  - Horaire 8h00 existe déjà')

        schedule_18h, created = CrontabSchedule.objects.get_or_create(
            minute='0',
            hour='18',
            day_of_week='*',
            day_of_month='*',
            month_of_year='*',
            timezone='Europe/Paris'
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Horaire 18h00 créé'))
        else:
            self.stdout.write('  - Horaire 18h00 existe déjà')

        # Créer la tâche du matin
        task_morning, created = PeriodicTask.objects.get_or_create(
            name='send-basket-notifications-morning',
            defaults={
                'task': 'panier.tasks.send_old_basket_notifications',
                'crontab': schedule_8h,
                'enabled': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Tâche du matin (8h00) créée'))
        else:
            # Mettre à jour si nécessaire
            task_morning.crontab = schedule_8h
            task_morning.enabled = True
            task_morning.save()
            self.stdout.write('  - Tâche du matin (8h00) existe déjà (mise à jour)')

        # Créer la tâche du soir
        task_evening, created = PeriodicTask.objects.get_or_create(
            name='send-basket-notifications-evening',
            defaults={
                'task': 'panier.tasks.send_old_basket_notifications',
                'crontab': schedule_18h,
                'enabled': True,
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✓ Tâche du soir (18h00) créée'))
        else:
            # Mettre à jour si nécessaire
            task_evening.crontab = schedule_18h
            task_evening.enabled = True
            task_evening.save()
            self.stdout.write('  - Tâche du soir (18h00) existe déjà (mise à jour)')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Configuration terminée avec succès !'))
        self.stdout.write('')
        self.stdout.write('Les notifications seront envoyées quotidiennement :')
        self.stdout.write('  • À 8h00 (heure de Paris)')
        self.stdout.write('  • À 18h00 (heure de Paris)')
