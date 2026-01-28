# CLAUDE.md - Contexte du projet PanierFacile

Ce fichier contient le contexte complet du projet pour maintenir la continuite entre les sessions.

## Vue d'ensemble

**PanierFacile** est une application Django permettant aux utilisateurs de :
- Creer des paniers de courses a partir de recettes
- Comparer les prix entre supermarches (Carrefour, Auchan)
- Utiliser un chatbot RAG pour des conseils culinaires

**URL Production** : https://panierfacile.music-music.fr/
**Deploiement** : Coolify (Docker)
**Base de donnees** : PostgreSQL
**Cache/Broker** : Redis
**Taches asynchrones** : Celery

---

## Architecture du Projet

### Structure des dossiers

```
panier_facile/
├── config/                 # Configuration Django (settings, urls, celery, wsgi, asgi)
├── authentication/         # App authentification (login, signup, OAuth Google)
├── panier/                 # App principale (paniers, courses, ingredients)
│   ├── views/              # Vues splitees par domaine
│   │   ├── __init__.py
│   │   ├── home.py         # Pages d'accueil
│   │   ├── courses.py      # CRUD courses
│   │   ├── paniers.py      # CRUD paniers
│   │   ├── stripe.py       # Paiements Stripe
│   │   ├── contact.py      # Contact et avis
│   │   ├── drive.py        # Geolocalisation (save_temp_location)
│   │   ├── price_comparison.py  # Comparaison de prix
│   │   ├── chatbot.py      # Chatbot RAG
│   │   └── health.py       # Health checks et notifications
│   ├── templates/panier/
│   └── management/commands/
├── contact/                # App contact (modeles ContactMessage, Review)
├── supermarkets/           # App supermarches
│   ├── models/             # ProductMatch, PriceComparison
│   ├── scrapers/           # CarrefourScraper, AuchanScraper
│   └── templates/supermarkets/
├── templates/              # Templates globaux
│   ├── base.html
│   └── pages/              # landing.html, home.html
├── static/
│   ├── css/
│   └── js/
│       ├── comparison.js   # Comparaison de prix
│       ├── chatbot.js
│       └── ...
└── docs/                   # Documentation technique
```

### Apps Django

| App | Description |
|-----|-------------|
| `config` | Configuration Django (anciennement `core`) |
| `authentication` | Authentification, OAuth Google |
| `panier` | Paniers, courses, ingredients, chatbot |
| `contact` | Messages de contact, avis utilisateurs |
| `supermarkets` | Scrapers, cache de prix, comparaisons |

---

## Historique des changements majeurs

### Phase 1-3 : Refactoring initial
- Suppression du manifest PWA (incompatible avec auth)
- Split des vues `panier/views.py` en modules (`panier/views/`)
- Creation de l'app `contact` (ContactMessage, Review)

### Phase 5 : App supermarkets
- Creation de `supermarkets/models/` (CarrefourProductMatch, AuchanProductMatch)
- Creation de `supermarkets/scrapers/` (CarrefourScraper, AuchanScraper)
- Scrapers avec playwright-stealth et interception API

### Phase 6 : Templates
- Reorganisation des templates par app
- Templates Drive deplaces vers `supermarkets/templates/`

### Phase 7 : Comparaison de prix (actuel)
- **Suppression du Drive** : Creation de paniers sur sites externes retiree (DataDome)
- **Suppression d'Intermarche** : Retire completement (DataDome incontournable)
- **Nouvelle fonctionnalite** : Comparaison de prix entre Carrefour et Auchan

#### Fichiers supprimes (Phase 7)
```
panier/intermarche_api.py
panier/intermarche_scraper.py
panier/views/supermarkets.py
supermarkets/scrapers/intermarche.py
supermarkets/models/intermarche.py
static/js/intermarche.js, auchan.js, carrefour.js, matching_progress.js, select_store.js
Templates Drive (11 fichiers)
```

#### Fichiers crees (Phase 7)
```
supermarkets/models/comparison.py          # PriceComparison
panier/views/price_comparison.py           # 4 vues comparaison
supermarkets/templates/supermarkets/
  ├── compare_prices.html
  ├── comparison_progress.html
  └── comparison_results.html
static/js/comparison.js
docs/phase7-price-comparison.md
```

---

## Fonctionnalites actuelles

### 1. Comparaison de prix
- **Flow** : detail_panier -> compare_prices -> comparison_progress -> comparison_results
- **Supermarches** : Carrefour, Auchan
- **Cache** : ProductMatch (24h)
- **Tache Celery** : `compare_supermarket_prices`

### 2. Chatbot RAG
- Documents charges au demarrage
- Embeddings OpenAI
- FAISS pour la recherche vectorielle

### 3. Authentification
- Login/Signup classique
- OAuth Google
- Profil utilisateur avec localisation

### 4. Paniers et courses
- CRUD complet
- Ingredients avec parsing des lignes

---

## Configuration Celery

### Services
- **web** : Gunicorn (APP_TYPE=web)
- **worker** : Celery worker (APP_TYPE=worker)
- **beat** : Celery beat scheduler (APP_TYPE=beat)

### Taches principales
```python
# panier/tasks.py
compare_supermarket_prices(panier_id, user_id, latitude, longitude)
match_carrefour_products(panier_id, user_id)
match_auchan_products(panier_id, user_id)
```

---

## Deploiement Coolify

### Variables d'environnement requises
```
DJANGO_SETTINGS_MODULE=config.settings
SECRET_KEY=...
DATABASE_URL=postgres://...
REDIS_URL=redis://...
OPENAI_API_KEY=...
STRIPE_SECRET_KEY=...
STRIPE_PUBLISHABLE_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

### Docker
- `Dockerfile` : Image Python 3.12 + Playwright
- `docker-entrypoint.sh` : Demarre web/worker/beat selon APP_TYPE

### Commandes de migration
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Problemes connus et solutions

### 1. DataDome (supermarches)
- **Probleme** : Protection anti-bot sur Intermarche, Carrefour, Auchan
- **Solution** : playwright-stealth + interception API JSON
- **Intermarche** : Retire (DataDome trop strict)

### 2. Migration contact app
- **Probleme** : `relation "panier_contactmessage" already exists`
- **Solution** : `python manage.py migrate contact --fake-initial`
- **Automatise** : Dans `docker-entrypoint.sh`

### 3. Terminal Coolify grise
- **Probleme** : Terminal web se fige
- **Solution** : Modifier `docker-entrypoint.sh` pour automatiser les commandes

---

## Modeles de donnees principaux

### panier.Panier
```python
user = ForeignKey(User)
date_creation = DateTimeField
courses = ManyToManyField(Course)
```

### panier.Course
```python
titre = CharField
ingredient = TextField  # Une ligne par ingredient
user = ForeignKey(User)
```

### supermarkets.PriceComparison
```python
user = ForeignKey(User)
panier = ForeignKey(Panier)
latitude, longitude = FloatField
carrefour_total, auchan_total = DecimalField
carrefour_found, auchan_found = IntegerField
cheapest_supermarket = CharField
created_at = DateTimeField
```

### supermarkets.CarrefourProductMatch / AuchanProductMatch
```python
ingredient_name = CharField
product_name = CharField
product_price = DecimalField
product_url = URLField
matched_at = DateTimeField  # Cache 24h
```

---

## URLs principales

```python
# panier/urls.py
/panier/                              # liste_paniers
/panier/<id>/                         # detail_panier
/panier/<id>/comparer/                # compare_prices
/panier/<id>/comparer/progress/<task>/ # comparison_progress
/panier/<id>/comparer/resultats/<id>/ # comparison_results
/panier/chatbot/                      # chatbot_ui
/panier/contact/                      # contact
```

---

## Extensibilite future

### Ajouter un supermarche
1. Creer `supermarkets/scrapers/nouveau.py`
2. Creer `supermarkets/models/nouveau.py` (NouveauProductMatch)
3. Modifier `compare_supermarket_prices` dans `panier/tasks.py`
4. Mettre a jour les templates de comparaison

### Supermarches potentiels
- Leclerc
- Lidl
- Casino
- Monoprix

---

## Commandes utiles

```bash
# Developpement local
python manage.py runserver
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info

# Production (Coolify)
# Les commandes sont automatisees via docker-entrypoint.sh

# Migrations
python manage.py makemigrations
python manage.py migrate
python manage.py migrate contact --fake-initial  # Si table existe deja

# Collectstatic
python manage.py collectstatic --noinput
```

---

## Documentation

- `docs/phase2-views-refactoring.md` - Split des vues
- `docs/phase3-models-refactoring.md` - App contact
- `docs/phase5-supermarkets-models.md` - App supermarkets
- `docs/phase6-templates-refactoring.md` - Templates
- `docs/phase7-price-comparison.md` - Comparaison de prix
- `docs/architecture.md` - Architecture globale

---

*Derniere mise a jour : Janvier 2026*
