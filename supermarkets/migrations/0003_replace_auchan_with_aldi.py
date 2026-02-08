"""
Migration custom : Remplacement Auchan par Aldi.

Gère le fait que les tables Cart (AuchanCart, CarrefourCart, IntermarcheCart)
n'ont jamais été créées en base (migration 0001 fakée).
On les supprime uniquement de l'état Django via SeparateDatabaseAndState.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('panier', '0001_initial'),
        ('supermarkets', '0002_remove_old_add_pricecomparison'),
    ]

    operations = [
        # ── Étape 1 : Supprimer les Cart models de l'état Django uniquement ──
        # Ces tables n'ont jamais été créées en base (0001 était fakée)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='AuchanCart'),
                migrations.DeleteModel(name='CarrefourCart'),
                migrations.DeleteModel(name='IntermarcheCart'),
            ],
            database_operations=[
                # Ne rien faire en base - les tables n'existent pas
            ],
        ),

        # ── Étape 2 : Supprimer IntermarcheProductMatch ──
        # Table existe en base, plus utilisée
        migrations.DeleteModel(name='IntermarcheProductMatch'),

        # ── Étape 3 : Supprimer AuchanProductMatch ──
        # Table panier_auchanproductmatch existe en base
        migrations.DeleteModel(name='AuchanProductMatch'),

        # ── Étape 4 : Créer AldiProductMatch ──
        migrations.CreateModel(
            name='AldiProductMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.CharField(default='scraping', help_text="ID du magasin Aldi (ou 'scraping' pour recherche générale)", max_length=20)),
                ('product_name', models.CharField(max_length=255)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('product_url', models.URLField(blank=True, null=True)),
                ('is_available', models.BooleanField(default=True)),
                ('match_score', models.FloatField(default=0.0, help_text="Score de correspondance avec l'ingrédient (0-1)")),
                ('image_url', models.URLField(blank=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aldi_matches', to='panier.ingredient')),
            ],
            options={
                'db_table': 'supermarkets_aldiproductmatch',
                'verbose_name': 'Produit Aldi matché',
                'verbose_name_plural': 'Produits Aldi matchés',
            },
        ),
        migrations.AddIndex(
            model_name='aldiproductmatch',
            index=models.Index(fields=['ingredient', 'store_id'], name='supermarket_ingredi_aldi_idx'),
        ),
        migrations.AddIndex(
            model_name='aldiproductmatch',
            index=models.Index(fields=['store_id', 'last_updated'], name='supermarket_store_i_aldi_idx'),
        ),

        # ── Étape 5 : Renommer les champs PriceComparison ──
        migrations.RenameField(
            model_name='pricecomparison',
            old_name='auchan_total',
            new_name='aldi_total',
        ),
        migrations.RenameField(
            model_name='pricecomparison',
            old_name='auchan_found',
            new_name='aldi_found',
        ),
        migrations.AlterField(
            model_name='pricecomparison',
            name='aldi_total',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Total estimé chez Aldi', max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='pricecomparison',
            name='aldi_found',
            field=models.IntegerField(default=0, help_text='Nombre de produits trouvés chez Aldi'),
        ),
        migrations.AlterField(
            model_name='pricecomparison',
            name='cheapest_supermarket',
            field=models.CharField(blank=True, help_text='Nom du supermarché le moins cher (carrefour, aldi)', max_length=20),
        ),
    ]
