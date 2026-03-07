# PanierFacile

## Présentation du projet

> _« On ne fait pas les courses deux fois. »_

## Motivation

Imaginez une famille de dix personnes. Le père part faire les courses du samedi matin. Il rentre à la maison avec dix sacs, pose tout sur le plan de travail et là, la mère réalise qu'il a oublié les packs de lait. Retourner au supermarché n'est pas une option : il y a les enfants à récupérer, le déjeuner à préparer, le week-end qui tourne à plein régime.

Ce scénario se répète chaque semaine dans des millions de foyers français. Les listes sur papier se perdent. Les SMS se noient dans les conversations. Les applications de notes ne sont pas partagées. Et au final, on oublie toujours quelque chose.

C'est pourquoi j'ai créé **PanierFacile**, une application de gestion de paniers de courses conçue pour les familles, afin que tout le monde sache en temps réel ce qu'il faut acheter, et que personne n'ait à faire deux fois le trajet.

## Ce que fait l'application

PanierFacile repose sur deux concepts simples : les **courses** et les **paniers**.

Une **course** est une liste d'articles à acheter — par exemple "Petit-déjeuner de la semaine" avec lait, céréales, pain, beurre, jus d'orange. Une course est créée une fois et peut être réutilisée indéfiniment.

Un **panier** regroupe plusieurs courses pour préparer une sortie en magasin complète. On y ajoute les courses de la semaine, celles des enfants, ce qui manque pour le dîner du soir.

Le point central de l'application : **le partage familial**. Tous les membres d'une même famille accèdent aux mêmes paniers et aux mêmes courses. Le père peut préparer le panier depuis son bureau, la mère y ajouter les articles oubliés depuis son téléphone, et l'aîné des enfants cocher ce qu'il a déjà mis dans le caddie en magasin.

L'application comprend également :

- **Un assistant IA** (chatbot RAG) pour aider les utilisateurs à naviguer dans l'application
- **Des rappels email automatiques** lorsqu'un panier n'a pas été mis à jour depuis deux semaines
- **Un système d'abonnement** avec trois mois d'essai gratuit, puis 1 €/mois via Stripe (mais j'ai decidé de rendre l'application gratuite).

## Comment je l'ai construit

Le backend est construit avec **Django 5.2** et **PostgreSQL**. Le partage familial repose sur une mécanique simple et efficace : les utilisateurs ayant le même nom de famille partagent automatiquement leurs paniers et leurs courses, sans invitation ni configuration complexe.

Les courses stockent leurs articles sous forme de texte multi-lignes, une ligne par article, ce qui rend la saisie rapide depuis un téléphone. Les paniers établissent une relation many-to-many avec les courses, permettant de réutiliser les mêmes listes d'une semaine à l'autre sans les recréer.

Les tâches asynchrones (rappels email, notifications) sont gérées par **Celery** avec **Redis** comme broker, planifiées via **Celery Beat**.

L'assistant IA est un pipeline **RAG (Retrieval-Augmented Generation)** construit avec **LangChain** et **OpenAI GPT**. Au démarrage, l'application indexe sa propre documentation via **FAISS** et répond aux questions des utilisateurs avec une connaissance précise de l'interface.

L'application est déployée en **Docker** sur **Coolify** (self-hosted), avec **Gunicorn** comme serveur WSGI et **WhiteNoise** pour les fichiers statiques.

## Les défis rencontrés

Le premier défi a été de trouver la bonne mécanique de partage familial. Imposer un système d'invitation avec des groupes aurait rendu l'application trop complexe pour un usage quotidien. J'ai opté pour un regroupement automatique par nom de famille, une approche simple qui correspond à la réalité des foyers français.

Le second défi a été l'intégration du système RAG sans impacter les performances au démarrage. Initialiser le vector store et les embeddings à chaque démarrage de worker était trop coûteux. J'ai résolu ce problème en tirant parti du hook `AppConfig.ready()` de Django pour ne charger le système qu'une seule fois par processus.

Enfin, la gestion des tâches Celery a nécessité une attention particulière : certaines tâches longues accédaient à l'ORM Django dans un contexte détecté comme asynchrone, ce qui provoquait des erreurs. La restructuration en phases distinctes (lecture cache, traitement, écriture DB) a permis de résoudre ces conflits proprement.

## Ce que j'ai appris

J'ai appris que la simplicité est un produit en soi. La décision de stocker les ingrédients sous forme de texte plutôt que dans des tables normalisées a rendu l'application dix fois plus rapide à prendre en main pour un utilisateur non-technique. La complexité technique ne doit pas se voir côté utilisateur.

J'ai aussi appris à tirer profit des hooks du cycle de vie Django pour bootstrapper des ressources coûteuses, et à concevoir des tâches asynchrones robustes qui séparent clairement les phases de lecture et d'écriture.

## Stack technique

| Couche             | Technologie                           |
| ------------------ | ------------------------------------- |
| Backend            | Django 5.2, Python 3.12               |
| Base de données    | PostgreSQL                            |
| Cache / Broker     | Redis                                 |
| Tâches asynchrones | Celery + Celery Beat                  |
| IA / RAG           | LangChain, OpenAI GPT, FAISS          |
| Paiement           | Stripe                                |
| Authentification   | django-allauth                        |
| Frontend           | Bootstrap 5, JavaScript               |
| Déploiement        | Docker, Gunicorn, WhiteNoise, Coolify |

## Accéder à l'application

L'application est disponible à l'adresse : [https://panier-facile.fr/](https://panier-facile.fr/)
