# Amazon Scraper

Un programme Python qui pilote Google Chrome avec Selenium pour chercher des produits sur Amazon.fr, puis enregistre ce qu'il trouve (nom, prix, note, lien, image) dans une base SQLite et dans des fichiers CSV.

C'est un projet réalisé dans le cadre de mes cours, organisé selon l'architecture MVC (modèle, vue, contrôleur).

## Ce que fait le programme

Au lancement, il ouvre une fenêtre Chrome et va sur amazon.fr. Ensuite, pour chacune des 9 recherches définies dans `config.py` (3 catégories avec 3 sous-catégories chacune), il parcourt jusqu'à 3 pages de résultats. Pour chaque produit trouvé, il :

1. relève le nom, le prix, la note, le vendeur (quand il est affiché), le lien et l'image ;
2. télécharge l'image du produit ;
3. enregistre le tout dans `db.sqlite` ;
4. met à jour les fichiers CSV de la sous-catégorie.

Un bilan s'affiche dans le terminal à la fin de chaque sous-catégorie (pages parcourues, produits trouvés, produits enregistrés, erreurs).

On peut relancer le programme autant de fois qu'on veut sans créer de doublons : un produit déjà connu est simplement mis à jour. Si Amazon n'affiche pas le prix ou la note lors d'un passage, l'ancienne valeur est conservée.

## Ce qu'il faut avoir avant de commencer

| Outil | À quoi il sert | Où le télécharger |
|---|---|---|
|---|---|---|
| Python 3.10 ou plus récent | exécuter le programme | https://www.python.org/downloads/ |
| Google Chrome | le navigateur que Selenium va piloter | https://www.google.com/chrome/ |
| Git | récupérer le projet depuis GitHub (facultatif, voir plus bas) | https://git-scm.com/downloads |
| Une connexion internet | pour Amazon et pour le premier lancement de Selenium | |

Sous Windows, pense à cocher la case **Add Python to PATH** pendant l'installation de Python, sinon la commande `python` ne sera pas reconnue.

Tu peux vérifier que tout est bien installé avec :

```bash
python --version
git --version
```

Il n'y a pas besoin de télécharger `chromedriver` à la main. Depuis Selenium 4, un outil intégré (Selenium Manager) télécharge tout seul le bon pilote pour ta version de Chrome au premier lancement. Il faut juste avoir internet à ce moment-là.

## Installation

### 1. Récupérer le projet

Avec Git :

```bash
git clone https://github.com/Emmanuelgael26dev/amazon-scraper.git
cd amazon-scraper
```


Sans Git, tu peux aussi cliquer sur le bouton vert **Code** de la page GitHub, choisir **Download ZIP**, puis extraire le dossier et ouvrir un terminal dedans.

### 2. Créer un environnement virtuel

Un environnement virtuel permet d'installer les bibliothèques du projet sans toucher au reste de ton ordinateur.

Sous Windows :

```bash
python -m venv .venv
.venv\Scripts\activate
```

Si PowerShell refuse d'activer l'environnement (message sur l'exécution de scripts désactivée), tape d'abord cette commande puis recommence l'activation :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Sous Linux ou macOS :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Quand l'environnement est actif, `(.venv)` apparaît au début de la ligne du terminal. À refaire à chaque nouveau terminal.

### 3. Installer les dépendances

```bash
python -m pip install -r requirements.txt
```

### 4. Lancer le programme

Toujours depuis le dossier qui contient `main.py` :

```bash
python main.py
```

Une fenêtre Chrome s'ouvre et navigue toute seule. Il vaut mieux ne pas la fermer ni cliquer dedans pendant l'exécution. Le terminal affiche l'avancement avec des messages `[INFO]`, `[SUCCÈS]`, `[AVERTISSEMENT]` ou `[ERREUR]`. Pour les 9 recherches complètes, compte plusieurs minutes.

Pour faire un test rapide, ouvre `config.py`, mets `MAX_PAGES_PER_SEARCH = 1` et mets en commentaire (avec `#`) quelques lignes de `CATEGORIES`.

## Ce que le programme crée

Le dépôt GitHub ne contient pas les données : le `.gitignore` exclut la base, les CSV et les images. Tout est généré au premier lancement, à la racine du projet :

```text
db.sqlite
technologie/
├── recap.csv
├── informatique/
│   ├── data.csv
│   ├── recap.csv
│   └── images/
├── smartphones/
└── audio/
maison/
sport_et_loisirs/
```

- `db.sqlite` : la base de données, avec deux tables (`products` pour les produits et `scraping_runs` pour l'historique des exécutions).
- `data.csv` (dans chaque sous-catégorie) : tous les produits de la sous-catégorie. Colonnes : `product_id`, `name`, `price`, `currency`, `seller`, `rating`, `product_url`, `image_path`, `scraped_at`.
- `recap.csv` (dans chaque sous-catégorie) : une ligne par lancement, avec les heures de début et de fin, les compteurs et le statut (`succes`, `partiel` ou `echec`).
- `recap.csv` (dans chaque catégorie) : le bilan global par sous-catégorie.
- `images/` : les photos des produits.

Certaines cellules peuvent être vides (prix, note, vendeur). Ce n'est pas forcément une erreur : Amazon n'affiche pas toujours ces informations sur la page de résultats. Le prix n'est aussi enregistré que s'il est complet avec les centimes (`599,99 €` est gardé, `599 €` est ignoré pour éviter un prix faux).

## Modifier la configuration

Tous les réglages sont dans `config.py`. Les principaux :

| Réglage | Rôle |
|---|---|
| `MAX_PAGES_PER_SEARCH` | nombre de pages de résultats parcourues par recherche (3 par défaut) |
| `TIMEOUT_SECONDS` | temps maximum d'attente d'un élément sur une page (15 s) |
| `CATEGORIES` | les catégories, sous-catégories et mots-clés recherchés |
| `BASE_URL` | l'adresse du site (https://www.amazon.fr) |
| `DB_PATH` | l'emplacement de la base SQLite |

Pour ajouter une recherche, il suffit d'ajouter une ligne dans `CATEGORIES` :

```python
"technologie": {
    "informatique": "ordinateur portable",
    "tablettes": "tablette tactile",      # nouvelle sous-catégorie
},
```

Les dossiers correspondants sont créés automatiquement au lancement.

## Dépendances

La seule bibliothèque que le code importe directement est **selenium**. Les autres lignes de `requirements.txt` (`trio`, `urllib3`, `certifi`, `websocket-client`, etc.) sont les bibliothèques dont Selenium a besoin pour fonctionner, elles s'installent toutes avec la commande `pip install -r requirements.txt`. Les versions sont fixées pour que le projet fonctionne de la même façon chez tout le monde.

Le reste (`csv`, `sqlite3`, `pathlib`, `urllib`, `decimal`...) fait partie de Python et n'a rien à installer.

## Organisation du code (MVC)

```text
amazon-scraper/
├── main.py                        # point d'entrée
├── config.py                      # tous les réglages
├── requirements.txt
├── models/
│   ├── database.py                # base SQLite
│   ├── amazon_scraper.py          # scraping avec Selenium
│   └── image_downloader.py        # téléchargement des images
├── views/
│   ├── csv_view.py                # fichiers CSV et dossiers de résultats
│   └── console_view.py            # affichage dans le terminal
├── controllers/
│   └── scraper_controller.py      # relie les modèles et les vues
└── utils/
    ├── logger.py                  # messages [INFO], [ERREUR]...
    └── helpers.py                 # date, conversion des prix, noms de fichiers
```

Les **modèles** s'occupent des données (collecte, base de données, images). Les **vues** s'occupent de ce que l'utilisateur obtient en sortie (CSV et affichage). Le **contrôleur** donne les ordres et fait le lien entre les deux.

## Problèmes fréquents

**`'python' n'est pas reconnu...`** : Python n'est pas dans le PATH. Réinstalle-le en cochant la case prévue, ou essaie la commande `py` à la place de `python`.

**`ModuleNotFoundError: No module named 'selenium'`** : l'environnement virtuel n'est pas activé, ou l'étape 3 n'a pas été faite.

**`ModuleNotFoundError: No module named 'models'` (ou `config`)** : le programme n'est pas lancé depuis le dossier qui contient `main.py`. Fais un `cd` vers ce dossier.

**Chrome ne s'ouvre pas ou erreur de pilote (`SessionNotCreatedException`, `NoSuchDriverException`)** : Chrome n'est pas installé ou pas à jour, ou il n'y avait pas de connexion internet au moment où Selenium cherchait le pilote. Mets Chrome à jour et relance.

**Message de CAPTCHA ou de page de blocage** : Amazon a repéré un comportement automatique. Le programme le détecte, l'indique dans le terminal et marque la sous-catégorie comme `partiel` ou `echec`. Attends un peu avant de relancer, évite d'enchaîner les exécutions et baisse `MAX_PAGES_PER_SEARCH`.

**Très peu de produits ou beaucoup de cases vides** : Amazon modifie régulièrement le code HTML de ses pages. Les sélecteurs se trouvent dans les fonctions `extract_*` de `models/amazon_scraper.py`, c'est là qu'il faudra corriger.

## À savoir avant de l'utiliser

Ce projet sert à apprendre le web scraping, sur de petites quantités de données publiques. Le programme fait des pauses entre les actions pour ne pas surcharger le site. Les conditions d'utilisation d'Amazon encadrent la collecte automatique de données : il ne faut donc pas s'en servir à des fins commerciales ni republier les données et les images collectées.

Aucune licence n'est définie pour le moment.