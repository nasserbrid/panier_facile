from django import forms
from .models import Course, Panier


# Formulaire pour Course

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['titre', 'ingredient']  
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control'}),
            'ingredient': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Mettre chaque ingrédient sur une nouvelle ligne, ex:\npain au lait\npain au chocolat\nconfiture'
            }),
        }



# Formulaire pour Panier
#On fait en sorte que l'utilisateur connecté soit automatiquement assigné au panier créé
class PanierForm(forms.ModelForm):
    class Meta:
        model = Panier
        fields = ['courses']  
        widgets = {
            'courses': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

# class PanierForm(forms.ModelForm):
#     class Meta:
#         model = Panier
#         fields = ['user', 'courses']  
#         widgets = {
#             'user': forms.Select(attrs={'class': 'form-control'}),
#             'courses': forms.SelectMultiple(attrs={'class': 'form-control'}),
#         }
