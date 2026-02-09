"""
Migration custom : Remplacement Carrefour par E.Leclerc.

- Supprime CarrefourProductMatch de l'état Django
- Crée LeclercProductMatch (nouvelle table)
- Renomme les champs carrefour_* → leclerc_* dans PriceComparison
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('panier', '0001_initial'),
        ('supermarkets', '0003_replace_auchan_with_aldi'),
    ]

    operations = [
        # ── Étape 1 : Supprimer CarrefourProductMatch ──
        # La table panier_carrefourproductmatch existe en base mais ne sera plus utilisée
        migrations.DeleteModel(name='CarrefourProductMatch'),

        # ── Étape 2 : Créer LeclercProductMatch ──
        migrations.CreateModel(
            name='LeclercProductMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.CharField(default='scraping', help_text="Identifiant du magasin Leclerc ou 'scraping'", max_length=20)),
                ('product_name', models.CharField(help_text='Nom du produit', max_length=255)),
                ('price', models.DecimalField(blank=True, decimal_places=2, help_text='Prix unitaire du produit', max_digits=10, null=True)),
                ('product_url', models.URLField(blank=True, help_text='URL du produit sur le site E.Leclerc', null=True)),
                ('is_available', models.BooleanField(default=True, help_text='Disponibilité du produit')),
                ('match_score', models.FloatField(default=0.0, help_text='Score de pertinence du matching (0.0 à 1.0)')),
                ('last_updated', models.DateTimeField(auto_now=True, help_text='Date de dernière mise à jour du match')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Date de création du match')),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='leclerc_matches', to='panier.ingredient')),
            ],
            options={
                'db_table': 'supermarkets_leclercproductmatch',
                'verbose_name': 'Correspondance produit E.Leclerc',
                'verbose_name_plural': 'Correspondances produits E.Leclerc',
            },
        ),
        migrations.AddIndex(
            model_name='leclercproductmatch',
            index=models.Index(fields=['ingredient', 'store_id'], name='supermarket_ingredi_lecl_idx'),
        ),
        migrations.AddIndex(
            model_name='leclercproductmatch',
            index=models.Index(fields=['store_id', 'last_updated'], name='supermarket_store_i_lecl_idx'),
        ),

        # ── Étape 3 : Renommer les champs PriceComparison carrefour → leclerc ──
        migrations.RenameField(
            model_name='pricecomparison',
            old_name='carrefour_total',
            new_name='leclerc_total',
        ),
        migrations.RenameField(
            model_name='pricecomparison',
            old_name='carrefour_found',
            new_name='leclerc_found',
        ),
        migrations.AlterField(
            model_name='pricecomparison',
            name='leclerc_total',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Total estimé chez E.Leclerc', max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='pricecomparison',
            name='leclerc_found',
            field=models.IntegerField(default=0, help_text='Nombre de produits trouvés chez E.Leclerc'),
        ),
        migrations.AlterField(
            model_name='pricecomparison',
            name='cheapest_supermarket',
            field=models.CharField(blank=True, help_text='Nom du supermarché le moins cher (leclerc, aldi)', max_length=20),
        ),
    ]
