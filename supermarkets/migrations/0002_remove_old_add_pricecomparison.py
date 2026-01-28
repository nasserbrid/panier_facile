# Generated migration for supermarkets app
# Only creates PriceComparison - Cart tables never existed in DB

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('panier', '0001_initial'),
        ('supermarkets', '0001_initial'),
    ]

    operations = [
        # Create PriceComparison only
        # Note: Cart tables (AuchanCart, CarrefourCart, IntermarcheCart)
        # were in migration 0001 but never actually created in DB
        # So we don't try to delete them here
        migrations.CreateModel(
            name='PriceComparison',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.FloatField(help_text="Latitude de l'utilisateur lors de la comparaison")),
                ('longitude', models.FloatField(help_text="Longitude de l'utilisateur lors de la comparaison")),
                ('carrefour_total', models.DecimalField(blank=True, decimal_places=2, help_text='Total estime chez Carrefour', max_digits=10, null=True)),
                ('auchan_total', models.DecimalField(blank=True, decimal_places=2, help_text='Total estime chez Auchan', max_digits=10, null=True)),
                ('carrefour_found', models.IntegerField(default=0, help_text='Nombre de produits trouves chez Carrefour')),
                ('auchan_found', models.IntegerField(default=0, help_text='Nombre de produits trouves chez Auchan')),
                ('total_ingredients', models.IntegerField(default=0, help_text="Nombre total d'ingredients dans le panier")),
                ('cheapest_supermarket', models.CharField(blank=True, help_text='Nom du supermarche le moins cher', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Date de creation de la comparaison')),
                ('panier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_comparisons', to='panier.panier')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='price_comparisons', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Comparaison de prix',
                'verbose_name_plural': 'Comparaisons de prix',
                'db_table': 'supermarkets_pricecomparison',
                'ordering': ['-created_at'],
            },
        ),
    ]
