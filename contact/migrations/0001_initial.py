# Generated migration for contact app
# This migration manages models that use existing database tables
# (migrated from panier app)

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ContactMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nom')),
                ('email', models.EmailField(max_length=254, verbose_name='Email')),
                ('subject', models.CharField(max_length=200, verbose_name='Sujet')),
                ('message', models.TextField(verbose_name='Message')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name="Date d'envoi")),
                ('is_read', models.BooleanField(default=False, verbose_name='Lu')),
                ('is_replied', models.BooleanField(default=False, verbose_name='Repondu')),
            ],
            options={
                'verbose_name': 'Message de contact',
                'verbose_name_plural': 'Messages de contact',
                'db_table': 'panier_contactmessage',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CustomerReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, help_text='Nom du client (peut etre anonyme)', max_length=100, verbose_name='Nom')),
                ('email', models.EmailField(blank=True, help_text='Email du client (non publie)', max_length=254, verbose_name='Email')),
                ('rating', models.IntegerField(choices=[(1, '1 etoile'), (2, '2 etoiles'), (3, '3 etoiles'), (4, '4 etoiles'), (5, '5 etoiles')], verbose_name='Note')),
                ('title', models.CharField(max_length=200, verbose_name='Titre')),
                ('review', models.TextField(verbose_name='Avis')),
                ('would_recommend', models.BooleanField(default=False, verbose_name='Recommande')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de creation')),
                ('is_approved', models.BooleanField(default=False, verbose_name='Approuve')),
                ('is_featured', models.BooleanField(default=False, verbose_name='Mis en avant')),
            ],
            options={
                'verbose_name': 'Avis client',
                'verbose_name_plural': 'Avis clients',
                'db_table': 'panier_customerreview',
                'ordering': ['-created_at'],
            },
        ),
    ]
