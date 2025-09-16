from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

class Course(models.Model):
    titre = models.CharField(max_length=255)
    ingredient = models.TextField()  

    def __str__(self):
        return self.titre

class Panier(models.Model):
    date_creation = models.DateTimeField(auto_now_add=True)

    # relation 1-N avec User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.CASCADE,
        related_name='paniers'
    )

    # relation N-N avec Course
    courses = models.ManyToManyField(Course, related_name='paniers', blank=True)

    def __str__(self):
        return f"Panier {self.id} de {self.user.username}"