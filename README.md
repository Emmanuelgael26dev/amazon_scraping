# Amazon Scraper 🛒

Un projet Python utilisant **Selenium** pour automatiser la navigation sur Amazon France et récupérer des informations sur les produits à partir des pages de résultats.

## 🎯 Objectif du projet

Ce projet permet de découvrir les bases du web scraping avec Python et Selenium : automatiser un navigateur, parcourir des pages web, extraire des informations et enregistrer les résultats pour les exploiter ultérieurement.

## ✨ Fonctionnalités

- Recherche de produits sur Amazon France.
- Extraction des informations disponibles sur les produits.
- Récupération des prix et des notes lorsqu'ils sont affichés.
- Récupération des URL des fiches produits.
- Téléchargement des images, si cette fonctionnalité est activée dans le code.
- Stockage local des données dans une base SQLite.
- Export des résultats au format CSV, si cette fonctionnalité est activée dans le code.
- Parcours de plusieurs pages de résultats, selon la configuration du scraper.

Les informations récupérables dépendent du contenu affiché par Amazon et de la structure de ses pages.

## 🧰 Technologies utilisées

- **Python** — langage de programmation.
- **Selenium** — automatisation du navigateur web.
- **SQLite** — stockage local des données, si utilisé par le projet.
- **CSV** — export des données, si activé.

## 📦 Prérequis

Avant de commencer, installe :

- Python.
- Google Chrome ou un navigateur compatible avec la configuration Selenium du projet.
- Git, si tu souhaites cloner le dépôt.

Selenium 4 dispose de Selenium Manager, qui peut gérer automatiquement le pilote du navigateur dans les configurations compatibles. Une installation manuelle du pilote n'est donc pas toujours nécessaire.

## 🚀 Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/TON-PSEUDO/amazon-scraper.git
cd amazon-scraper
```

Remplace `TON-PSEUDO` par ton nom d'utilisateur GitHub.

### 2. Créer un environnement virtuel

Sous Windows :

```bash
python -m venv .venv
```

Activer l'environnement :

```bash
.venv\Scripts\activate
```

Sous Linux ou macOS :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Installer les dépendances

```bash
python -m pip install -r requirements.txt
```

### 4. Lancer le programme

Exécute le fichier Python qui contient le point d'entrée du scraper.

Par exemple, si le fichier principal s'appelle `main.py` :

```bash
python main.py
```

Adapte cette commande au nom réel du fichier principal de ton projet.

## 🗂️ Organisation du projet

L'organisation exacte dépend des fichiers présents dans le dépôt. Une structure possible est :

```text
amazon-scraper/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── db.sqlite
├── exports/
└── images/
```

Les fichiers `db.sqlite`, `exports/` et `images/` représentent des données locales générées par le programme. Ils ne sont pas nécessairement versionnés sur GitHub.

## 📊 Données récupérées

Selon les informations disponibles sur les pages de résultats, le scraper peut récupérer :

| Champ | Description |
|---|---|
| Nom | Nom du produit |
| Prix | Prix affiché, lorsqu'il est disponible |
| Note | Note affichée, lorsqu'elle existe |
| URL | Lien vers la fiche du produit |
| Image | Image du produit, si disponible |
| Vendeur | Nom du vendeur, uniquement s'il est accessible dans les données analysées |

Certains champs peuvent être absents. Une donnée manquante ne signifie pas nécessairement que le programme a échoué.

## ⚠️ Limites et bonnes pratiques

- La structure HTML d'Amazon peut changer et nécessiter une mise à jour des sélecteurs.
- Amazon peut limiter l'accès ou afficher une page de vérification.
- Les résultats dépendent de la recherche, de la disponibilité des produits et des informations effectivement affichées.
- Il est recommandé de limiter la fréquence des requêtes et de respecter les conditions d'utilisation du site ainsi que les règles applicables à la collecte des données.

Ce projet est destiné à l'apprentissage et à l'expérimentation du web scraping.

## 📄 Licence

Aucune licence n'est définie pour le moment. Si tu souhaites autoriser explicitement la réutilisation du code, ajoute une licence adaptée au dépôt.

---

Développé avec Python et Selenium.