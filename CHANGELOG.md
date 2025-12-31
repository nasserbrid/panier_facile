# Changelog PanierFacile

## 2025-12-31 - Sécurité et Refactoring

### 1. Protection contre les abus avec Rate Limiting

**Pourquoi :** Protéger l'application contre les utilisations abusives (spam, brute force, surcharge serveur).

**Modifications :**

#### Formulaire de Contact
- **Fichier :** `panier/views.py:1630`
- **Rate limit :** 5 soumissions/heure par IP
- **Pourquoi :** Éviter le spam massif d'emails vers l'administrateur

#### Authentification
- **Fichiers :** `authentication/views.py:28`, `authentication/urls.py:6`
- **Login :** 10 tentatives/minute par IP
- **Signup :** 3 inscriptions/heure par IP
- **Pourquoi :** Protection contre les attaques brute force et création de comptes en masse

#### Chatbot
- **Fichier :** `panier/views.py:1181`
- **Rate limit :** 30 requêtes/minute par utilisateur ou IP
- **Pourquoi :** Éviter la surcharge du serveur et la consommation excessive de l'API OpenAI

#### Création de Paniers/Courses
- **Fichiers :** `panier/views.py:362`, `panier/views.py:472`
- **Rate limit :** 50 créations/heure par utilisateur
- **Pourquoi :** Prévenir la pollution de la base de données

**Impact :** Les utilisateurs normaux ne seront pas affectés. Les abus sont bloqués avec des messages d'erreur clairs.

---

### 2. Masquage des Coordonnées GPS

**Pourquoi :** Protection de la vie privée des utilisateurs.

**Modifications :**
- **Fichiers :**
  - `authentication/templates/authentication/profile.html:96-101`
  - `panier/templates/panier/select_store_for_drive.html:46-51`
- **Changement :** Suppression de l'affichage "Lat: X, Long: Y" en clair
- **Conservation :** Seule l'adresse lisible est affichée

**Impact :** Les coordonnées GPS restent fonctionnelles en backend mais ne sont plus visibles par l'utilisateur.

---

### 3. Masquage Temporaire du Drive Intermarché

**Pourquoi :** La fonctionnalité est bloquée par DataDome (CAPTCHA anti-bot).

**Modifications :**
- **Fichier :** `panier/templates/panier/detail_panier.html:60-64`
- **Changement :** Bouton "Faire un Drive" commenté
- **Code préservé :** Prêt à être réactivé quand le problème DataDome sera résolu

**Impact :** Les utilisateurs ne voient plus le bouton non fonctionnel. Pas de frustration liée aux erreurs.

---

### 4. Formulaire de Contact Accessible

**Pourquoi :** Permettre aux utilisateurs de contacter l'administrateur facilement.

**Modifications :**
- **Fichier :** `templates/base.html:45-49`, `panier/views.py:1630-1695`
- **Ajout :** Lien "Contact" dans la navbar
- **Notification :** Email automatique envoyé à l'administrateur à chaque soumission
- **Sauvegarde :** Messages stockés en base de données

**Impact :** Canal de communication direct entre utilisateurs et administrateur.

---

### 5. Refactoring JavaScript (Séparation des Préoccupations)

**Pourquoi :** Améliorer la maintenabilité, respecter les bonnes pratiques, faciliter le débogage.

**Modifications :**

#### Création de `static/js/base.js`
- **Contenu :** Logique Stripe checkout (anciennement inline dans base.html)
- **Avantages :**
  - Code réutilisable
  - Mise en cache par le navigateur
  - Débogage plus facile

#### Mise à jour de `static/js/chatbot.js`
- **Changement :** Lecture de l'URL depuis attribut `data-url` au lieu de variable globale
- **Avantages :** Pas de variables JavaScript globales polluantes

#### Modification de `templates/base.html`
- **Suppression :** Scripts inline (120 lignes → 0 lignes)
- **Ajout :** Éléments `data-*` pour passer les variables Django au JavaScript
- **Migration :** onclick → addEventListener avec data-attributes

**Impact :**
- Code plus propre et organisé
- Performance améliorée (mise en cache)
- Conformité CSP (Content Security Policy) facilitée pour le futur

---

### 6. Notifications Email Automatiques (Déjà en place)

**Statut :** Confirmé fonctionnel via logs Celery Beat

**Système :**
- **Fichier :** `panier/tasks.py:27-124`
- **Fréquence :** 2 fois/jour (8h et 18h, heure de Paris)
- **Déclencheur :** Paniers créés il y a 14 jours
- **Email :** Rappel avec liste des courses

**Impact :** Engagement utilisateur maintenu, rappels automatiques pour refaire les courses.

---

## Récapitulatif des Fichiers Modifiés

### Backend (Django)
- `authentication/views.py` - CustomLoginView + rate limiting signup
- `authentication/urls.py` - Utilisation de CustomLoginView
- `panier/views.py` - Rate limiting (contact, chatbot, paniers/courses)

### Frontend (Templates)
- `templates/base.html` - Extraction JS inline, ajout Contact navbar
- `panier/templates/panier/contact.html` - Déjà existant (pas de modif majeure)
- `panier/templates/panier/detail_panier.html` - Masquage bouton Drive
- `authentication/templates/authentication/profile.html` - Masquage GPS
- `panier/templates/panier/select_store_for_drive.html` - Masquage GPS

### JavaScript
- `static/js/base.js` - NOUVEAU - Logique Stripe
- `static/js/chatbot.js` - Migration vers data-attributes

---

## Prochaines Étapes Recommandées

1. **Drive Intermarché :** Trouver une solution pour contourner DataDome (proxies résidentiels, API officielle)
2. **Tests :** Vérifier le rate limiting en environnement de production
3. **Refactoring JS :** Continuer l'extraction des scripts inline des autres templates (profile.html, select_store_for_drive.html)
4. **Monitoring :** Surveiller les logs pour détecter d'éventuelles tentatives d'abus

---

## Notes de Déploiement

**Aucune migration de base de données requise.**

Les changements sont uniquement au niveau de la logique applicative et du frontend.

Le système fonctionne immédiatement après déploiement sans intervention supplémentaire.
