from django.test import TestCase
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from panier.models import Panier, Course

# On récupère le modèle User configuré dans settings.AUTH_USER_MODEL
User = get_user_model()


class LandingPageViewTest(TestCase):
    def test_landing_page_status_code(self):
        # Arrange
        client = Client()

        # Act
        response = client.get(reverse("landing"))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "panier/landing.html")


class HomeViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="nasser", password="testpass")
        self.client.login(username="nasser", password="testpass")
        self.panier = Panier.objects.create(user=self.user)

    def test_home_view_authenticated(self):
        # Arrange
        url = reverse("home")

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "panier/home.html")
        self.assertIn("paniers", response.context)
        self.assertEqual(len(response.context["paniers"]), 1)


class AjouterCourseAuPanierTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="nasser", password="testpass")
        self.client.login(username="nasser", password="testpass")
        self.panier = Panier.objects.create(user=self.user)
        self.course = Course.objects.create(titre="Test course")

    def test_ajouter_course_au_panier(self):
        # Arrange
        # url = reverse("ajouter_course_au_panier", args=[self.panier.id, self.course.id])
        url = reverse("ajouter_course_au_panier", args=[self.panier.id])


        # Act
        response = self.client.get(url)

        # Assert
        self.assertRedirects(response, reverse("detail_panier", args=[self.panier.id]))
        self.assertIn(self.course, self.panier.courses.all())
        
    
    
 