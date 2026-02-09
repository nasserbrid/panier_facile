"""
Migration custom : Remplacement Aldi par Lidl.

Supprime AldiProductMatch, crée LidlProductMatch,
renomme les colonnes aldi_* -> lidl_* dans PriceComparison.
Migration fakée sur Coolify (tables gérées manuellement via entrypoint).
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('panier', '0001_initial'),
        ('supermarkets', '0004_replace_carrefour_with_leclerc'),
    ]

    operations = [
        # ── Étape 1 : Supprimer AldiProductMatch ──
        migrations.DeleteModel(name='AldiProductMatch'),

        # ── Étape 2 : Créer LidlProductMatch ──
        migrations.CreateModel(
            name='LidlProductMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.CharField(default='scraping', help_text="ID du magasin Lidl (ou 'scraping' pour recherche générale)", max_length=20)),
                ('product_name', models.CharField(max_length=255)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('product_url', models.URLField(blank=True, null=True)),
                ('is_available', models.BooleanField(default=True)),
                ('match_score', models.FloatField(default=0.0, help_text="Score de correspondance avec l'ingrédient (0-1)")),
                ('image_url', models.URLField(blank=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lidl_matches', to='panier.ingredient')),
            ],
            options={
                'db_table': 'supermarkets_lidlproductmatch',
                'verbose_name': 'Produit Lidl matché',
                'verbose_name_plural': 'Produits Lidl matchés',
            },
        ),
        migrations.AddIndex(
            model_name='lidlproductmatch',
            index=models.Index(fields=['ingredient', 'store_id'], name='supermarket_ingredi_lidl_idx'),
        ),
        migrations.AddIndex(
            model_name='lidlproductmatch',
            index=models.Index(fields=['store_id', 'last_updated'], name='supermarket_store_i_lidl_idx'),
        ),

        # ── Étape 3 : Renommer les champs PriceComparison ──
        migrations.RenameField(
            model_name='pricecomparison',
            old_name='aldi_total',
            new_name='lidl_total',
        ),
        migrations.RenameField(
            model_name='pricecomparison',
            old_name='aldi_found',
            new_name='lidl_found',
        ),
        migrations.AlterField(
            model_name='pricecomparison',
            name='lidl_total',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Total estimé chez Lidl', max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='pricecomparison',
            name='lidl_found',
            field=models.IntegerField(default=0, help_text='Nombre de produits trouvés chez Lidl'),
        ),
        migrations.AlterField(
            model_name='pricecomparison',
            name='cheapest_supermarket',
            field=models.CharField(blank=True, help_text='Nom du supermarché le moins cher (leclerc, lidl)', max_length=20),
        ),
    ]
