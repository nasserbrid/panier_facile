from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'

    def ready(self):
        """
        Import les signaux lorsque l'application Django démarre.
        La méthode ready() est appelée automatiquement par Django.
        """
        import authentication.signals
