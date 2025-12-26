from django import forms


class ContactForm(forms.Form):
    """Formulaire de contact pour que les utilisateurs puissent contacter l'équipe"""

    name = forms.CharField(
        max_length=100,
        label="Nom",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom complet'
        })
    )

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre.email@exemple.com'
        })
    )

    subject = forms.CharField(
        max_length=200,
        label="Sujet",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Sujet de votre message'
        })
    )

    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Votre message...'
        })
    )


class ReviewForm(forms.Form):
    """Formulaire d'avis clients pour recueillir les retours"""

    RATING_CHOICES = [
        (5, '⭐⭐⭐⭐⭐ Excellent'),
        (4, '⭐⭐⭐⭐ Très bien'),
        (3, '⭐⭐⭐ Bien'),
        (2, '⭐⭐ Moyen'),
        (1, '⭐ Insuffisant'),
    ]

    name = forms.CharField(
        max_length=100,
        label="Nom (optionnel)",
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre nom (laissez vide pour rester anonyme)'
        })
    )

    email = forms.EmailField(
        label="Email (optionnel)",
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'votre.email@exemple.com'
        }),
        help_text="Votre email ne sera pas publié"
    )

    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        label="Note",
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )

    title = forms.CharField(
        max_length=200,
        label="Titre de votre avis",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Résumé de votre expérience'
        })
    )

    review = forms.CharField(
        label="Votre avis",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': 'Partagez votre expérience avec PanierFacile...'
        })
    )

    would_recommend = forms.BooleanField(
        label="Je recommanderais PanierFacile à mes proches",
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
