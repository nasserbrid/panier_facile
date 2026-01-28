# Generated migration for supermarkets app
# This migration manages models that use existing database tables
# (migrated from panier app)
# Run with: python manage.py migrate supermarkets --fake

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('panier', '0001_initial'),
    ]

    operations = [
        # Intermarche models
        migrations.CreateModel(
            name='IntermarcheProductMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.CharField(default='scraping', help_text="Identifiant du magasin Intermarche", max_length=20)),
                ('intermarche_product_id', models.CharField(blank=True, help_text='ID unique du produit Intermarche', max_length=100, null=True)),
                ('intermarche_product_ean13', models.CharField(blank=True, help_text='Code-barres EAN13', max_length=13)),
                ('intermarche_item_parent_id', models.CharField(blank=True, help_text='ID parent', max_length=100, null=True)),
                ('product_name', models.CharField(help_text='Nom du produit', max_length=255)),
                ('product_label', models.CharField(blank=True, help_text='Libelle du produit', max_length=255)),
                ('product_brand', models.CharField(blank=True, help_text='Marque du produit', max_length=100)),
                ('price', models.DecimalField(blank=True, decimal_places=2, help_text='Prix unitaire', max_digits=10, null=True)),
                ('product_price', models.DecimalField(blank=True, decimal_places=2, help_text='Prix (deprecated)', max_digits=10, null=True)),
                ('product_url', models.URLField(blank=True, help_text='URL du produit', null=True)),
                ('product_image_url', models.URLField(blank=True, help_text='URL image')),
                ('is_available', models.BooleanField(default=True, help_text='Disponibilite')),
                ('match_score', models.FloatField(default=0.0, help_text='Score de matching')),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='intermarche_matches', to='panier.ingredient')),
            ],
            options={
                'verbose_name': 'Correspondance produit Intermarche',
                'verbose_name_plural': 'Correspondances produits Intermarche',
                'db_table': 'panier_intermarcheproductmatch',
            },
        ),
        migrations.CreateModel(
            name='IntermarcheCart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.CharField(help_text='ID du magasin', max_length=20)),
                ('store_name', models.CharField(blank=True, help_text='Nom du magasin', max_length=255)),
                ('anonymous_cart_id', models.CharField(help_text='UUID panier anonyme', max_length=100, unique=True)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, help_text='Total en euros', max_digits=10)),
                ('items_count', models.IntegerField(default=0, help_text='Nombre articles')),
                ('status', models.CharField(choices=[('draft', 'Brouillon'), ('sent', 'Envoye'), ('completed', 'Finalise'), ('failed', 'Echec')], default='draft', max_length=20)),
                ('sync_response', models.JSONField(blank=True, help_text='Reponse API', null=True)),
                ('error_message', models.TextField(blank=True, help_text='Message erreur')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('panier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='intermarche_carts', to='panier.panier')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='intermarche_carts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Panier Intermarche',
                'verbose_name_plural': 'Paniers Intermarche',
                'db_table': 'panier_intermarchecart',
                'ordering': ['-created_at'],
            },
        ),
        # Carrefour models
        migrations.CreateModel(
            name='CarrefourProductMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.CharField(default='scraping', help_text='ID du magasin Carrefour', max_length=20)),
                ('product_name', models.CharField(help_text='Nom du produit', max_length=255)),
                ('price', models.DecimalField(blank=True, decimal_places=2, help_text='Prix unitaire', max_digits=10, null=True)),
                ('product_url', models.URLField(blank=True, help_text='URL du produit', null=True)),
                ('is_available', models.BooleanField(default=True, help_text='Disponibilite')),
                ('match_score', models.FloatField(default=0.0, help_text='Score de matching')),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='carrefour_matches', to='panier.ingredient')),
            ],
            options={
                'verbose_name': 'Correspondance produit Carrefour',
                'verbose_name_plural': 'Correspondances produits Carrefour',
                'db_table': 'panier_carrefourproductmatch',
            },
        ),
        migrations.CreateModel(
            name='CarrefourCart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.CharField(help_text='ID du magasin', max_length=20)),
                ('store_name', models.CharField(blank=True, help_text='Nom du magasin', max_length=255)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, help_text='Total en euros', max_digits=10)),
                ('items_count', models.IntegerField(default=0, help_text='Nombre articles')),
                ('status', models.CharField(choices=[('draft', 'Brouillon'), ('sent', 'Envoye'), ('completed', 'Finalise'), ('failed', 'Echec')], default='draft', max_length=20)),
                ('error_message', models.TextField(blank=True, help_text='Message erreur')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('panier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='carrefour_carts', to='panier.panier')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='carrefour_carts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Panier Carrefour',
                'verbose_name_plural': 'Paniers Carrefour',
                'db_table': 'panier_carrefourcart',
                'ordering': ['-created_at'],
            },
        ),
        # Auchan models
        migrations.CreateModel(
            name='AuchanProductMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.CharField(default='scraping', help_text='ID du magasin Auchan', max_length=20)),
                ('product_name', models.CharField(max_length=255)),
                ('price', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('product_url', models.URLField(blank=True, null=True)),
                ('is_available', models.BooleanField(default=True)),
                ('match_score', models.FloatField(default=0.0, help_text='Score de correspondance')),
                ('image_url', models.URLField(blank=True, null=True)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auchan_matches', to='panier.ingredient')),
            ],
            options={
                'verbose_name': 'Produit Auchan matche',
                'verbose_name_plural': 'Produits Auchan matches',
                'db_table': 'panier_auchanproductmatch',
            },
        ),
        migrations.CreateModel(
            name='AuchanCart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('store_id', models.CharField(max_length=20)),
                ('store_name', models.CharField(blank=True, max_length=255)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('items_count', models.IntegerField(default=0)),
                ('status', models.CharField(choices=[('draft', 'Brouillon'), ('completed', 'Complete'), ('exported', 'Exporte')], default='draft', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('panier', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auchan_carts', to='panier.panier')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='auchan_carts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Panier Auchan',
                'verbose_name_plural': 'Paniers Auchan',
                'db_table': 'panier_auchancart',
                'ordering': ['-created_at'],
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name='intermarcheproductmatch',
            index=models.Index(fields=['ingredient', 'store_id'], name='panier_inte_ingredi_idx'),
        ),
        migrations.AddIndex(
            model_name='intermarcheproductmatch',
            index=models.Index(fields=['store_id', 'last_updated'], name='panier_inte_store_i_idx'),
        ),
        migrations.AddIndex(
            model_name='intermarchecart',
            index=models.Index(fields=['user', 'status'], name='panier_inte_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='intermarchecart',
            index=models.Index(fields=['store_id', 'created_at'], name='panier_inte_store_i_cart_idx'),
        ),
        migrations.AddIndex(
            model_name='carrefourproductmatch',
            index=models.Index(fields=['ingredient', 'store_id'], name='panier_carr_ingredi_idx'),
        ),
        migrations.AddIndex(
            model_name='carrefourproductmatch',
            index=models.Index(fields=['store_id', 'last_updated'], name='panier_carr_store_i_idx'),
        ),
        migrations.AddIndex(
            model_name='carrefourcart',
            index=models.Index(fields=['user', 'status'], name='panier_carr_user_id_idx'),
        ),
        migrations.AddIndex(
            model_name='carrefourcart',
            index=models.Index(fields=['store_id', 'created_at'], name='panier_carr_store_i_cart_idx'),
        ),
        migrations.AddIndex(
            model_name='auchanproductmatch',
            index=models.Index(fields=['ingredient', 'store_id'], name='panier_auch_ingredi_idx'),
        ),
        migrations.AddIndex(
            model_name='auchanproductmatch',
            index=models.Index(fields=['store_id', 'last_updated'], name='panier_auch_store_i_idx'),
        ),
    ]
