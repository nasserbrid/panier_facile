# Guide de déploiement Celery sur Coolify

## Architecture

L'application PanierFacile nécessite maintenant 4 services sur Coolify:

1. **Application Web Django** (déjà déployé)
2. **Redis** - Broker pour Celery
3. **Celery Worker** - Exécute les tâches asynchrones
4. **Celery Beat** - Scheduler pour les tâches périodiques

## Prérequis

- ✅ Application Django déjà déployée sur Coolify
- ✅ Base de données PostgreSQL configurée
- ⏳ Service Redis à ajouter
- ⏳ Service Celery Worker à ajouter
- ⏳ Service Celery Beat à ajouter

## Étapes de déploiement

### 1. Créer un service Redis dans Coolify

1. Dans votre projet Coolify, cliquez sur **"Add new service"**
2. Sélectionnez **"Redis"**
3. Configuration:
   - **Name**: `panier-redis`
   - **Version**: `7-alpine` (recommandé)
   - **Port**: `6379` (par défaut)
   - **Persistence**: Activé (pour ne pas perdre les données au redémarrage)

4. Déployez le service Redis

5. Notez l'URL interne de connexion (format: `redis://panier-redis:6379/0`)

### 2. Ajouter la variable d'environnement REDIS_URL

Dans votre service Web Django (panier-facile):

1. Allez dans **Settings → Environment Variables**
2. Ajoutez:
   ```
   REDIS_URL=redis://panier-redis:6379/0
   ```
   (Remplacez `panier-redis` par le nom exact de votre service Redis dans Coolify)

3. Redéployez l'application Web pour prendre en compte la nouvelle variable

### 3. Appliquer les migrations Django

Avant de lancer Celery, vous devez:

1. Exécuter les migrations pour créer les tables `notification_sent` et `notification_sent_date`:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

2. Appliquer les migrations de `django-celery-beat`:
   ```bash
   python manage.py migrate django_celery_beat
   ```

### 4. Créer le service Celery Worker

1. Dans Coolify, créez un nouveau service de type **"Docker Image"**
2. Configuration:
   - **Name**: `panier-celery-worker`
   - **Source**: Même repository Git que l'application web
   - **Branch**: `main` (ou votre branche de production)
   - **Dockerfile**: Utiliser le même Dockerfile
   - **Command Override**:
     ```bash
     celery -A core worker --loglevel=info --concurrency=2
     ```

3. Variables d'environnement (copier toutes les variables de l'application Web + ajouter):
   ```
   REDIS_URL=redis://panier-redis:6379/0
   DATABASE_URL=<votre_url_postgresql>
   SECRET_KEY=<votre_secret_key>
   EMAIL_HOST_USER=<votre_email>
   EMAIL_HOST_PASSWORD=<votre_mot_de_passe_email>
   DEFAULT_FROM_EMAIL=<votre_email>
   # ... toutes les autres variables de l'app web
   ```

4. **Network**: Assurez-vous que le worker est dans le même réseau Docker que Redis et PostgreSQL

5. Déployez le service

### 5. Créer le service Celery Beat

1. Dans Coolify, créez un nouveau service de type **"Docker Image"**
2. Configuration:
   - **Name**: `panier-celery-beat`
   - **Source**: Même repository Git
   - **Branch**: `main`
   - **Dockerfile**: Utiliser le même Dockerfile
   - **Command Override**:
     ```bash
     celery -A core beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
     ```

3. Variables d'environnement (mêmes que Celery Worker):
   ```
   REDIS_URL=redis://panier-redis:6379/0
   DATABASE_URL=<votre_url_postgresql>
   SECRET_KEY=<votre_secret_key>
   # ... toutes les autres variables
   ```

4. **Important**: Un seul processus Celery Beat doit tourner à la fois!

5. Déployez le service

### 6. Vérifier que tout fonctionne

#### Test 1: Vérifier que Celery Worker est connecté

Dans les logs du worker (`panier-celery-worker`), vous devriez voir:
```
[INFO/MainProcess] Connected to redis://panier-redis:6379/0
[INFO/MainProcess] celery@hostname ready.
[INFO/MainProcess] Registered tasks:
    panier.tasks.send_old_basket_notifications
    panier.tasks.test_celery
```

#### Test 2: Vérifier que Celery Beat est actif

Dans les logs de beat (`panier-celery-beat`), vous devriez voir:
```
[INFO/MainProcess] beat: Starting...
[INFO/MainProcess] Scheduler: DatabaseScheduler
[INFO/MainProcess] Schedule:
    send-basket-notifications-morning schedule: <crontab: 0 8 * * * ...>
    send-basket-notifications-evening schedule: <crontab: 0 18 * * * ...>
```

#### Test 3: Tester l'envoi de tâche manuel

Vous pouvez tester en exécutant dans le shell Django:
```python
from panier.tasks import test_celery
result = test_celery.delay()
print(result.get())  # Devrait afficher "Celery is working!"
```

## Configuration des tâches planifiées

Les tâches sont configurées dans `core/celery.py`:

- **Matin**: 8h00 (heure de Paris)
- **Soir**: 18h00 (heure de Paris)

Ces horaires sont en timezone `Europe/Paris` configurée dans `settings.py`.

## Monitoring et Logs

### Voir les logs en temps réel

Dans Coolify, pour chaque service:
- Web: Logs de l'application Django
- Worker: Logs des tâches Celery exécutées
- Beat: Logs du scheduler (quand les tâches sont planifiées)
- Redis: Logs de connexion

### Commandes utiles

Si vous avez accès SSH au serveur:

```bash
# Voir les workers actifs
celery -A core inspect active

# Voir les tâches planifiées
celery -A core inspect scheduled

# Purger toutes les tâches en attente
celery -A core purge

# Statistiques des workers
celery -A core inspect stats
```

## Désactiver l'ancien système GitHub Actions

Une fois Celery déployé et fonctionnel:

1. Désactivez le workflow `.github/workflows/notification.yml`
2. Ou supprimez le fichier complètement

L'ancien système utilisait GitHub Actions pour appeler Render, ce qui n'est plus nécessaire avec Celery.

## Résumé de l'architecture finale

```
┌─────────────────────────────────────────────────────┐
│                    Coolify VPS                       │
│                                                      │
│  ┌──────────────┐    ┌─────────────┐               │
│  │   Web App    │───▶│  PostgreSQL │               │
│  │  (Gunicorn)  │    └─────────────┘               │
│  └──────┬───────┘                                   │
│         │                                            │
│         │        ┌─────────────┐                    │
│         └───────▶│    Redis    │◀────────┐          │
│                  └─────────────┘         │          │
│                        ▲                 │          │
│                        │                 │          │
│         ┌──────────────┴────┐   ┌───────┴────────┐ │
│         │  Celery Worker    │   │  Celery Beat   │ │
│         │  (Execute tasks)  │   │  (Scheduler)   │ │
│         └───────────────────┘   └────────────────┘ │
│                                                      │
└─────────────────────────────────────────────────────┘

Tâches planifiées:
- 8h00 : Envoi notifications paniers 14j
- 18h00 : Envoi notifications paniers 14j
```

## Troubleshooting

### Problème: Worker ne démarre pas
**Solution**: Vérifiez que `REDIS_URL` est correctement configuré et que Redis est accessible

### Problème: Beat ne lance pas les tâches
**Solution**:
- Vérifiez que les migrations `django_celery_beat` sont appliquées
- Vérifiez le fuseau horaire `CELERY_TIMEZONE = 'Europe/Paris'`
- Un seul processus Beat doit tourner

### Problème: Notifications non envoyées
**Solution**:
- Vérifiez les logs du worker
- Vérifiez que `EMAIL_HOST_USER` et `EMAIL_HOST_PASSWORD` sont configurés
- Testez manuellement: `python manage.py shell` puis exécutez la tâche

### Problème: "ModuleNotFoundError: No module named 'celery'"
**Solution**: Assurez-vous que `requirements.txt` contient bien celery, redis et django-celery-beat

## Variables d'environnement requises

Toutes les variables suivantes doivent être configurées pour Web, Worker ET Beat:

```bash
# Django
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=panier-facile.fr,www.panier-facile.fr
DATABASE_URL=postgresql://...

# Email
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
DEFAULT_FROM_EMAIL=...
EMAIL_PORT=587

# Stripe
SECRET_KEY_STRIPE=...
PUBLISHABLE_KEY_STRIPE=...
STRIPE_PRICE_ID=...

# Redis (nouveau)
REDIS_URL=redis://panier-redis:6379/0

# Domaine
DOMAIN=https://panier-facile.fr
```

## Prochaines étapes

1. ✅ Déployer Redis
2. ✅ Configurer REDIS_URL
3. ✅ Appliquer les migrations
4. ✅ Déployer Celery Worker
5. ✅ Déployer Celery Beat
6. ✅ Tester l'envoi de notifications
7. ✅ Surveiller les logs pendant 24h
8. ✅ Désactiver GitHub Actions
