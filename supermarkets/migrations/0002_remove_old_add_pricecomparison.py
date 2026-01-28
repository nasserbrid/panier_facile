# Generated migration for supermarkets app
# Removes old Drive-related models and adds PriceComparison

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
        # Remove old indexes first
        migrations.RemoveIndex(
            model_name='intermarcheproductmatch',
            name='panier_inte_ingredi_idx',
        ),
        migrations.RemoveIndex(
            model_name='intermarcheproductmatch',
            name='panier_inte_store_i_idx',
        ),
        migrations.RemoveIndex(
            model_name='intermarchecart',
            name='panier_inte_user_id_idx',
        ),
        migrations.RemoveIndex(
            model_name='intermarchecart',
            name='panier_inte_store_i_cart_idx',
        ),
        migrations.RemoveIndex(
            model_name='carrefourcart',
            name='panier_carr_user_id_idx',
        ),
        migrations.RemoveIndex(
            model_name='carrefourcart',
            name='panier_carr_store_i_cart_idx',
        ),

        # Delete old models
        migrations.DeleteModel(
            name='IntermarcheProductMatch',
        ),
        migrations.DeleteModel(
            name='IntermarcheCart',
        ),
        migrations.DeleteModel(
            name='CarrefourCart',
        ),
        migrations.DeleteModel(
            name='AuchanCart',
        ),

        # Create PriceComparison
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
