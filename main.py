# ==============================================================================
# PROJET : SCRAPER E-COMMERCE AMAZON.FR (ARCHITECTURE PROPRE & PÉDAGOGIQUE)
# ==============================================================================
# OBJECTIF DU PROGRAMME :
# Ce programme automatise la collecte de données publiques de produits sur le
# site Amazon.fr à l'aide de la bibliothèque Selenium.
#
# POURQUOI UNE « CLEAN ARCHITECTURE » (ARCHITECTURE PROPRE) ?
# Pour qu'un programme informatique soit facile à lire, à maintenir et à expliquer,
# on ne mélange jamais tout au même endroit. Ce fichier est découpé en 7 couches
# indépendantes (chacune a une seule responsabilité précise) :
#
#   1. CONFIGURATION        : Tous les réglages (catégories, limites, chemins).
#   2. OUTILS & LOGS        : Nettoyage des textes/prix, dates et affichage console.
#   3. BASE DE DONNÉES      : Sauvegarde durable sans doublons dans SQLite (db.sqlite).
#   4. GESTION DES IMAGES   : Téléchargement des photos produit sur l'ordinateur.
#   5. SCRAPER SELENIUM     : Pilotage du navigateur Chrome comme un humain.
#   6. EXPORTATION CSV      : Création des tableaux Excel/CSV (data.csv, recap.csv).
#   7. ORCHESTRATEUR (MAIN) : Le chef d'orchestre qui relie toutes les étapes.
# ==============================================================================

# --- IMPORTATION DES BIBLIOTHÈQUES STANDARDS DE PYTHON ---
import csv                                      # Pour lire et écrire des fichiers tabulaires .csv
import mimetypes                                # Pour deviner l'extension d'une image (.jpg, .png) selon son type
import re                                       # Pour utiliser les Expressions Régulières (filtrer du texte)
import sqlite3                                  # Pour gérer la base de données locale SQLite sans serveur externe
import time                                     # Pour faire des pauses (attendre quelques secondes comme un humain)
from datetime import datetime                   # Pour récupérer la date et l'heure exactes de la collecte
from decimal import Decimal, InvalidOperation   # Pour manipuler les prix avec précision sans erreurs d'arrondi
from pathlib import Path                        # Pour gérer les chemins de dossiers sur Windows, Mac et Linux
from urllib.parse import urljoin, urlparse, unquote  # Pour analyser, reconstruire et décoder les adresses web (URL)
from urllib.request import Request, urlopen     # Pour télécharger les fichiers images depuis Internet

# --- IMPORTATION DE LA BIBLIOTHÈQUE EXTERNE SELENIUM ---
# Selenium permet à Python de prendre le contrôle d'un vrai navigateur web (Google Chrome).
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,                           # Erreur déclenchée quand une page met trop de temps à répondre
    WebDriverException,                         # Erreur générale liée au navigateur Chrome
)
from selenium.webdriver.common.by import By     # Permet de cibler un élément HTML (par ID, classe CSS, XPath...)
from selenium.webdriver.common.keys import Keys # Permet de simuler les touches du clavier (comme la touche Entrée)
from selenium.webdriver.support import expected_conditions as EC  # Conditions d'attente (ex: élément visible)
from selenium.webdriver.support.ui import WebDriverWait           # Attente intelligente jusqu'à ce qu'un élément apparaisse


# ==============================================================================
# COUCHE 1 : CONFIGURATION ET PARAMÈTRES GLOBAUX
# ==============================================================================

# Path(__file__).resolve().parent récupère automatiquement le dossier dans lequel
# se trouve notre fichier main.py, peu importe l'ordinateur sur lequel on le lance.
ROOT = Path(__file__).resolve().parent

# Chemin complet vers le fichier de base de données SQLite.
DB_PATH = ROOT / "db.sqlite"

# Adresse d'accueil d'Amazon France.
# ASTUCE ANTI-BOT : On ouvre toujours la page d'accueil avant de chercher,
# exactement comme le ferait un véritable client humain.
BASE_URL = "https://www.amazon.fr"

# Temps maximal (en secondes) accordé à Selenium pour trouver un élément sur la page.
TIMEOUT_SECONDS = 15

# Nombre maximal de pages à parcourir pour chaque recherche.
# Astuce pour l'étudiant : tu peux mettre 1 ou 2 pour tester rapidement ton code,
# puis remettre 3 (ou plus) pour la collecte finale demandée par le professeur.
MAX_PAGES_PER_SEARCH = 3

# Dictionnaire imbriqué définissant 3 grandes catégories et 3 sous-catégories chacune.
# Structure : "nom_dossier_categorie": { "nom_dossier_sous_categorie": "mot clé tapé sur Amazon" }
# L'étudiant peut très facilement commenter (#) une ligne pour en retirer, ou en ajouter.
CATEGORIES = {
    "technologie": {
        "informatique": "ordinateur portable",
        "smartphones": "smartphone debloque",
        "audio": "casque bluetooth",
    },
    "maison": {
        "cuisine": "cafetiere expresso",
        "menage": "aspirateur sans fil",
        "eclairage": "lampe de bureau led",
    },
    "sport_et_loisirs": {
        "fitness": "tapis de course",
        "camping": "tente de camping",
        "jeux_video": "manette sans fil",
    },
}

# Liste ordonnée des colonnes du fichier data.csv (les produits récoltés).
# Ces colonnes seront TOUJOURS présentes dans le CSV, même si certaines cellules sont vides.
PRODUCT_FIELDS = [
    "product_id",   # Identifiant unique Amazon du produit (appelé code ASIN, ex: B0BTCMBB42)
    "name",         # Titre complet du produit
    "price",        # Prix numérique en euros (ex: 599.99) ou vide si non affiché sur la page de recherche
    "currency",     # Devise monétaire ("EUR" si un prix est présent, sinon vide)
    "seller",       # Nom du vendeur s'il est écrit sur la carte de recherche, sinon vide
    "rating",       # Note moyenne des clients (ex: "4,5 sur 5 étoiles"), sinon vide
    "product_url",  # Lien direct et propre vers la fiche du produit
    "image_path",   # Chemin vers l'image téléchargée sur l'ordinateur
    "scraped_at",   # Date et heure exactes auxquelles le produit a été collecté
]

# Colonnes du fichier recap.csv situé dans chaque dossier de sous-catégorie (historique des lancements).
RUN_FIELDS = [
    "run_id",         # Numéro unique de l'exécution
    "start_time",     # Heure de début
    "end_time",       # Heure de fin
    "pages_scraped",  # Nombre de pages Amazon parcourues
    "products_found", # Nombre de produits valides trouvés sur Amazon
    "products_saved", # Nombre de produits enregistrés dans la base SQLite
    "errors",         # Nombre d'anomalies mineures (ex: carte sans titre, image cassée)
    "failures",       # Nombre d'échecs critiques d'enregistrement
    "status",         # Résultat final : "succes", "partiel" ou "echec"
]

# Colonnes du fichier recap.csv situé dans chaque dossier de catégorie (bilan global cumulé).
CATEGORY_SUMMARY_FIELDS = [
    "subcategory",
    "pages_scraped",
    "products_found",
    "products_saved",
    "errors",
    "failures",
    "status",
]


# ==============================================================================
# COUCHE 2 : JOURNALISATION (LOGS) ET FONCTIONS UTILITAIRES
# ==============================================================================

def log_info(message):
    """Affiche une étape normale du programme dans le terminal."""
    print(f"[INFO] {message}")


def log_success(message):
    """Affiche une étape qui a parfaitement réussi."""
    print(f"[SUCCÈS] {message}")


def log_warning(message):
    """
    Affiche un avertissement non bloquant.
    Le programme continue de tourner normalement.
    """
    print(f"[AVERTISSEMENT] {message}")


def log_diagnostic(asin, message):
    """
    Explique de façon pédagogique pourquoi un produit précis (identifié par son ASIN)
    ne possède pas certaines informations facultatives (prix, note, vendeur) sur Amazon.
    """
    print(f"    -> [DIAGNOSTIC ASIN {asin}] {message}")


def log_error(message):
    """Affiche une erreur importante qui a empêché une action de se réaliser."""
    print(f"[ERREUR] {message}")


def now():
    """
    Retourne la date et l'heure actuelles au format international ISO 8601
    (Exemple : '2026-10-23T14:30:05').
    """
    return datetime.now().isoformat(timespec="seconds")


def parse_price(price_text):
    """
    Transforme un prix écrit en français (texte) en un nombre décimal Python (float).
    RÈGLE STRICTE : On n'enregistre jamais uniquement la partie entière si les
    centimes manquent, afin d'éviter des prix faux ou incomplets.

    Exemples :
    - '599,99 €'   devient 599.99
    - '1 299,00 €' devient 1299.00
    - '599 €'      devient None (rejeté car les centimes sont absents)
    - '' ou None   devient None
    """
    if not price_text:
        return None

    # On retire les espaces normaux, les espaces insécables (\u00a0 et \u202f) et le symbole €
    cleaned = (
        price_text
        .replace("\u00a0", "")
        .replace("\u202f", "")
        .replace(" ", "")
        .replace("€", "")
        .strip()
    )

    # Expression régulière :
    # ^(\d+)    -> Doit commencer par 1 ou plusieurs chiffres (partie entière)
    # [,\.]     -> Suivi d'une virgule ou d'un point
    # (\d{2})$  -> Et se terminer obligatoirement par exactement 2 chiffres (les centimes)
    match = re.search(r"^(\d+)[,\.](\d{2})$", cleaned)
    if not match:
        return None

    # On reconstruit le nombre avec un point décimal (standard informatique)
    normalized = f"{match.group(1)}.{match.group(2)}"

    try:
        value = Decimal(normalized)
        if not value.is_finite():
            return None
        return float(value)
    except InvalidOperation:
        return None


def create_slug(text):
    """
    Nettoie le nom d'un produit pour en faire un nom de fichier image valide.
    Exemple : 'PC Portable HP 15,6" !' -> 'pc-portable-hp-15-6'
    On limite aussi la longueur à 60 caractères pour éviter que Windows ne refuse
    des chemins de fichiers trop longs (limite MAX_PATH sur Windows).
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return (text[:60].strip("-")) or "produit"


def write_csv(destination, fields, rows):
    """
    Écrit une liste de dictionnaires Python dans un fichier CSV.
    - 'utf-8-sig' permet à Microsoft Excel d'afficher correctement les accents français (é, è, à).
    - Toutes les colonnes de 'fields' sont conservées, même si une valeur vaut None.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fields,
            restval="",
            extrasaction="ignore",
        )
        # Écrit la première ligne contenant les titres des colonnes
        writer.writeheader()

        # Écrit chaque ligne en remplaçant None par une cellule vide ""
        for row in rows:
            clean_row = {
                field: ("" if row.get(field) is None else row.get(field))
                for field in fields
            }
            writer.writerow(clean_row)


def create_directories(category, subcategory):
    """
    Crée l'arborescence des dossiers pour une catégorie et une sous-catégorie :
    Exemple :
      technologie/
      ├── recap.csv
      └── informatique/
          ├── data.csv
          ├── recap.csv
          └── images/
    """
    category_dir = ROOT / category
    subcategory_dir = category_dir / subcategory
    images_dir = subcategory_dir / "images"

    # Crée les dossiers s'ils n'existent pas encore
    images_dir.mkdir(parents=True, exist_ok=True)

    data_file = subcategory_dir / "data.csv"
    subcategory_recap = subcategory_dir / "recap.csv"
    category_recap = category_dir / "recap.csv"

    # Initialise les fichiers CSV avec leurs entêtes uniquement s'ils n'existent pas encore
    if not data_file.exists():
        write_csv(data_file, PRODUCT_FIELDS, [])

    if not subcategory_recap.exists():
        write_csv(subcategory_recap, RUN_FIELDS, [])

    if not category_recap.exists():
        write_csv(category_recap, CATEGORY_SUMMARY_FIELDS, [])

    return (
        category_dir,
        subcategory_dir,
        images_dir,
        data_file,
        subcategory_recap,
        category_recap,
    )


# ==============================================================================
# COUCHE 3 : PERSISTANCE DES DONNÉES (BASE DE DONNÉES SQLITE)
# ==============================================================================

def get_connection():
    """
    Ouvre une connexion vers le fichier db.sqlite.
    sqlite3.Row permet d'accéder aux colonnes par leur nom (ex: row["price"])
    comme dans un dictionnaire Python.
    """
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_database():
    """
    Crée les deux tables de la base de données si elles n'existent pas encore :
    1. 'products'      : stocke tous les produits uniques.
    2. 'scraping_runs' : garde l'historique de chaque exécution du programme.
    """
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL,
                currency TEXT,
                seller TEXT,
                rating TEXT,
                product_url TEXT NOT NULL,
                image_path TEXT,
                scraped_at TEXT NOT NULL,
                UNIQUE(product_url, subcategory)
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS scraping_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                subcategory TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                pages_scraped INTEGER DEFAULT 0,
                products_found INTEGER DEFAULT 0,
                products_saved INTEGER DEFAULT 0,
                errors INTEGER DEFAULT 0,
                failures INTEGER DEFAULT 0,
                status TEXT NOT NULL
            )
        """)

        # Mise à jour automatique si une ancienne base db.sqlite n'avait pas la colonne pages_scraped
        existing_cols = [
            row["name"]
            for row in connection.execute("PRAGMA table_info(scraping_runs)").fetchall()
        ]
        if "pages_scraped" not in existing_cols:
            connection.execute(
                "ALTER TABLE scraping_runs ADD COLUMN pages_scraped INTEGER DEFAULT 0"
            )


def start_run(category, subcategory):
    """Crée une nouvelle ligne dans l'historique au démarrage d'une sous-catégorie."""
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO scraping_runs (
                category,
                subcategory,
                start_time,
                status
            )
            VALUES (?, ?, ?, ?)
        """, (
            category,
            subcategory,
            now(),
            "en_cours",
        ))
        return cursor.lastrowid


def finish_run(run_id, summary):
    """Met à jour la ligne d'historique à la fin de la collecte avec tous les compteurs."""
    with get_connection() as connection:
        connection.execute("""
            UPDATE scraping_runs
            SET end_time = ?,
                pages_scraped = ?,
                products_found = ?,
                products_saved = ?,
                errors = ?,
                failures = ?,
                status = ?
            WHERE id = ?
        """, (
            summary["end_time"],
            summary["pages_scraped"],
            summary["products_found"],
            summary["products_saved"],
            summary["errors"],
            summary["failures"],
            summary["status"],
            run_id,
        ))


def save_product(product):
    """
    Enregistre un produit dans SQLite sans jamais créer de doublons :
    - Si le produit existe déjà (même ASIN ou même URL dans la sous-catégorie),
      il est mis à jour.
    - La fonction SQL COALESCE(nouvelle_valeur, ancienne_valeur) permet de conserver
      l'ancien prix ou l'ancienne note si jamais Amazon ne l'affichait pas cette fois-ci.
    """
    with get_connection() as connection:
        existing_by_id = connection.execute("""
            SELECT id
            FROM products
            WHERE product_id = ? AND subcategory = ?
        """, (product["product_id"], product["subcategory"])).fetchone()

        if existing_by_id:
            connection.execute("""
                UPDATE products
                SET name = ?,
                    price = COALESCE(?, price),
                    currency = COALESCE(?, currency),
                    seller = COALESCE(?, seller),
                    rating = COALESCE(?, rating),
                    product_url = ?,
                    image_path = COALESCE(?, image_path),
                    scraped_at = ?
                WHERE id = ?
            """, (
                product["name"],
                product["price"],
                product["currency"],
                product["seller"],
                product["rating"],
                product["product_url"],
                product["image_path"],
                product["scraped_at"],
                existing_by_id["id"],
            ))
            return

        connection.execute("""
            INSERT INTO products (
                product_id,
                category,
                subcategory,
                name,
                price,
                currency,
                seller,
                rating,
                product_url,
                image_path,
                scraped_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(product_url, subcategory)
            DO UPDATE SET
                product_id = excluded.product_id,
                name = excluded.name,
                price = COALESCE(excluded.price, products.price),
                currency = COALESCE(excluded.currency, products.currency),
                seller = COALESCE(excluded.seller, products.seller),
                rating = COALESCE(excluded.rating, products.rating),
                image_path = COALESCE(excluded.image_path, products.image_path),
                scraped_at = excluded.scraped_at
        """, (
            product["product_id"],
            product["category"],
            product["subcategory"],
            product["name"],
            product["price"],
            product["currency"],
            product["seller"],
            product["rating"],
            product["product_url"],
            product["image_path"],
            product["scraped_at"],
        ))


def get_products(category, subcategory):
    """Lit tous les produits d'une sous-catégorie depuis SQLite pour les exporter en CSV."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                product_id,
                name,
                price,
                currency,
                seller,
                rating,
                product_url,
                image_path,
                scraped_at
            FROM products
            WHERE category = ?
              AND subcategory = ?
            ORDER BY id
        """, (category, subcategory)).fetchall()

        return [dict(row) for row in rows]


def get_runs(category, subcategory):
    """Lit tout l'historique des exécutions d'une sous-catégorie."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                id AS run_id,
                start_time,
                end_time,
                pages_scraped,
                products_found,
                products_saved,
                errors,
                failures,
                status
            FROM scraping_runs
            WHERE category = ?
              AND subcategory = ?
            ORDER BY id
        """, (category, subcategory)).fetchall()

        return [dict(row) for row in rows]


def get_category_summary(category):
    """Calcule la somme des statistiques par sous-catégorie pour le fichier recap.csv de la catégorie."""
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                subcategory,
                SUM(pages_scraped) AS pages_scraped,
                SUM(products_found) AS products_found,
                SUM(products_saved) AS products_saved,
                SUM(errors) AS errors,
                SUM(failures) AS failures,
                CASE
                    WHEN SUM(
                        CASE WHEN status = 'echec'
                        THEN 1 ELSE 0 END
                    ) > 0 THEN 'echec'
                    WHEN SUM(
                        CASE WHEN status = 'partiel'
                        THEN 1 ELSE 0 END
                    ) > 0 THEN 'partiel'
                    ELSE 'succes'
                END AS status
            FROM scraping_runs
            WHERE category = ?
            GROUP BY subcategory
        """, (category,)).fetchall()

        return [dict(row) for row in rows]


# ==============================================================================
# COUCHE 4 : SERVICE DE TÉLÉCHARGEMENT DES IMAGES
# ==============================================================================

def download_image(image_url, destination_without_extension):
    """
    Télécharge l'image du produit à partir de son URL et l'enregistre dans le dossier 'images/'.
    RÈGLE MÉTIER : Si le téléchargement échoue, on retourne None mais on ne jette pas le produit.
    """
    if not image_url:
        return None

    try:
        # On ajoute un en-tête User-Agent classique pour que le serveur d'images accepte la requête
        request = Request(
            image_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )

        with urlopen(request, timeout=15) as response:
            content_type = (
                response.headers.get("Content-Type", "")
                .split(";")[0]
                .lower()
            )

            # On vérifie que le fichier reçu est bien une image
            if not content_type.startswith("image/"):
                raise ValueError("Le serveur n'a pas retourné une image valide.")

            extension = mimetypes.guess_extension(content_type) or ".jpg"
            destination = Path(str(destination_without_extension) + extension)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(response.read())

            # Retourne un chemin relatif propre avec des slashs '/' (ex: 'technologie/informatique/images/...')
            return destination.relative_to(ROOT).as_posix()

    except Exception as error:
        log_warning(f"Échec du téléchargement de l'image ({image_url}) : {error}")
        return None


# ==============================================================================
# COUCHE 5 : SCRAPER SELENIUM (NAVIGATION HUMAINE & EXTRACTION DOM)
# ==============================================================================

def create_stealth_driver():
    """
    Crée et configure une fenêtre Google Chrome pilotée par Selenium.
    POURQUOI CES OPTIONS ?
    Par défaut, Selenium active une variable interne (navigator.webdriver = true)
    qui crie aux sites web : « Je suis un robot ! ».
    Ces options désactivent ce drapeau pour naviguer discrètement.
    """
    options = webdriver.ChromeOptions()
    options.page_load_strategy = "eager"
    options.add_argument("--window-size=1365,900")
    options.add_argument("--lang=fr-FR")

    # Masque les indicateurs d'automatisation de Chrome
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(45)
    driver.set_script_timeout(20)

    # Remplace navigator.webdriver par 'undefined' avant le chargement de chaque page
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                """
            },
        )
    except Exception:
        pass

    return driver


def get_element_text(parent, css_selector):
    """
    Lit le texte d'un élément HTML à l'intérieur d'une fiche produit.
    SUBTILITÉ AMAZON :
    Les prix (.a-offscreen) et les notes (.a-icon-alt) sont souvent cachés visuellement
    pour les lecteurs d'écran. En Selenium, `.text` renvoie parfois du vide sur ces éléments.
    On utilise donc `.get_attribute("textContent")` en secours pour toujours récupérer le texte.
    """
    try:
        elements = parent.find_elements(By.CSS_SELECTOR, css_selector)
        if not elements:
            return ""
        first_el = elements[0]
        text = (first_el.text or "").strip()
        if not text:
            text = (first_el.get_attribute("textContent") or "").strip()
        return text
    except Exception:
        return ""


def click_continue_if_present(driver):
    """
    Gère l'écran intermédiaire d'Amazon ET la bannière de cookies.

    EXPLICATION DU PIÈGE AMAZON (CORRIGÉ ICI) :
    Sur la page interstitielle d'Amazon France, l'encadré d'information écrit :
    « Cliquez sur le bouton ci-dessous pour continuer VOS achats »
    MAIS le bouton jaune lui-même contient le texte :
    « Continuer LES achats » !
    Cette fonction cherche donc les deux formulations (« Continuer les achats »
    ET « Continuer vos achats »), ainsi que le bouton de soumission du formulaire,
    puis clique automatiquement dessus sans aucune intervention manuelle.
    """
    clicked_interstitial = False

    # Liste des sélecteurs XPath couvrant toutes les variantes du bouton jaune d'accueil
    interstitial_xpaths = [
        # 1. Recherche exacte ou partielle sur "Continuer les achats" (visible sur la capture)
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continuer les achats')]",
        "//input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continuer les achats')]",
        "//*[contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continuer les achats')]",
        # 2. Recherche sur la variante "Continuer vos achats"
        "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continuer vos achats')]",
        "//input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continuer vos achats')]",
        "//*[contains(translate(normalize-space(text()), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continuer vos achats')]",
        # 3. Sélecteur générique du bouton jaune de la page intermédiaire Amazon
        "//button[@type='submit' and contains(@class, 'a-button-text')]",
    ]

    # On attend jusqu'à 4 secondes au cas où le bouton mettrait un court instant à s'afficher
    end_time = time.time() + 4.0
    while time.time() < end_time and not clicked_interstitial:
        # Si la barre de recherche principale est déjà là, pas besoin d'attendre le bouton intermédiaire
        if driver.find_elements(By.CSS_SELECTOR, "#twotabsearchtextbox"):
            break

        for xpath in interstitial_xpaths:
            try:
                elements = driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if element.is_displayed():
                        element.click()
                        log_success("Bouton intermédiaire (« Continuer les/vos achats ») détecté et cliqué automatiquement !")
                        clicked_interstitial = True
                        time.sleep(2.0)
                        break
                if clicked_interstitial:
                    break
            except Exception:
                continue

        if not clicked_interstitial:
            time.sleep(0.4)

    # Une fois sur la vraie page d'accueil, on ferme aussi la bannière de cookies si elle apparaît
    cookie_selectors = [
        "#sp-cc-accept",
        "input#sp-cc-accept",
        "button#sp-cc-accept",
    ]
    for selector in cookie_selectors:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for btn in buttons:
                if btn.is_displayed():
                    btn.click()
                    log_info("Bannière de cookies acceptée automatiquement.")
                    time.sleep(1.0)
                    return True
        except Exception:
            continue

    if not clicked_interstitial:
        log_info("Aucun écran « Continuer les achats » bloquant détecté. Poursuite normale.")

    return clicked_interstitial


def detect_problem_page(driver):
    """
    Vérifie si Amazon affiche un vrai CAPTCHA (puzzle / lettres à recopier)
    ou une page d'erreur technique.
    Attention : Si le bouton « Continuer les achats » est présent, on tente d'abord
    de le cliquer avant de conclure à un blocage.
    """
    # Si la barre de recherche ou des fiches produits sont présentes, tout va bien !
    try:
        if driver.find_elements(By.CSS_SELECTOR, "#twotabsearchtextbox"):
            return False
        if driver.find_elements(By.CSS_SELECTOR, 'div[data-component-type="s-search-result"][data-asin]'):
            return False
    except Exception:
        pass

    # Si c'est simplement l'écran "Continuer les achats", on le clique et on revérifie
    if click_continue_if_present(driver):
        return False

    try:
        body_elements = driver.find_elements(By.TAG_NAME, "body")
        body_text = (body_elements[0].text if body_elements else driver.page_source).lower()
    except Exception:
        return True

    problem_phrases = [
        "toutes nos excuses",
        "robot check",
        "saisissez les caractères que vous voyez",
        "enter the characters you see below",
        "verify you're not a robot",
        "vérifier que vous n'êtes pas un robot",
        "sorry, we just need to make sure you're not a robot",
    ]

    for phrase in problem_phrases:
        if phrase in body_text:
            log_error(f"Page de blocage ou CAPTCHA détectée (« {phrase} »).")
            return True

    return False


def extract_product_name(card):
    """
    Récupère le titre du produit en essayant plusieurs sélecteurs CSS.
    RÈGLE : Si le nom est introuvable, retourne "" (et la carte sera ignorée).
    """
    selectors = [
        "h2 a span",
        "h2 span",
        "h2",
    ]
    for selector in selectors:
        title = get_element_text(card, selector)
        if title:
            return title
    return ""


def extract_product_url(card, asin=""):
    """
    Récupère l'adresse web (URL) du produit.
    POURQUOI DÉCODER L'URL AVEC unquote() ?
    Les produits sponsorisés sur Amazon ont des liens de redirection publicitaire
    comme '/sspa/click?...&url=%2Fdp%2FB0BTCMBB42'.
    unquote() transforme '%2Fdp%2F' en '/dp/', ce qui permet d'extraire le vrai
    lien propre du produit : 'https://www.amazon.fr/dp/B0BTCMBB42'.
    """
    try:
        links = card.find_elements(By.CSS_SELECTOR, "h2 a[href], a.a-link-normal[href], a[href]")
        for link in links:
            href = (link.get_attribute("href") or "").strip()
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            decoded_href = unquote(href)

            # Recherche de l'identifiant ASIN (10 caractères) après /dp/ ou /gp/product/
            dp_match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", decoded_href)
            if dp_match:
                return f"{BASE_URL}/dp/{dp_match.group(1)}"

            if "/dp/" in decoded_href or "/gp/product/" in decoded_href:
                complete_url = urljoin(BASE_URL, href)
                parsed_url = urlparse(complete_url)
                if parsed_url.netloc in ("www.amazon.fr", "amazon.fr"):
                    return f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    except Exception:
        pass

    # Solution de secours : si la carte HTML possède un code ASIN valide de 10 caractères
    if re.match(r"^[A-Z0-9]{10}$", asin):
        return f"{BASE_URL}/dp/{asin}"

    return ""


def extract_product_price(card):
    """
    Essaie plusieurs sélecteurs CSS pour récupérer le prix du produit.
    RÈGLE : Ne jamais enregistrer uniquement la partie entière si les centimes manquent.

    POURQUOI UN PRODUIT PEUT-IL NE PAS AVOIR DE PRIX DANS DATA.CSV ?
    Sur la page de recherche Amazon, certains produits n'affichent aucun prix direct :
    1. Produits avec variantes (taille/couleur/capacité) où Amazon oblige à cliquer
       sur la fiche pour voir le tarif.
    2. Produits vendus uniquement par des vendeurs tiers (bouton « Voir toutes les offres »).
    3. Produits temporairement en rupture de stock.
    Dans ces cas-là, cette fonction renvoie None (et la cellule 'price' reste vide dans data.csv).
    """
    # Méthode 1 : Lecture du prix complet dans les balises d'accessibilité .a-offscreen
    offscreen_selectors = [
        '.a-price[data-a-color="base"] span.a-offscreen',
        '.a-price:not([data-a-strike="true"]) span.a-offscreen',
        ".a-price span.a-offscreen",
    ]

    for selector in offscreen_selectors:
        try:
            elements = card.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                raw_text = (element.get_attribute("textContent") or element.text or "").strip()
                if parse_price(raw_text) is not None:
                    return raw_text
        except Exception:
            continue

    # Méthode 2 : Assemblage manuel de la partie entière (.a-price-whole) + centimes (.a-price-fraction)
    try:
        containers = card.find_elements(By.CSS_SELECTOR, '.a-price:not([data-a-strike="true"])')
        for container in containers:
            whole = get_element_text(container, ".a-price-whole")
            fraction = get_element_text(container, ".a-price-fraction")

            whole_digits = re.sub(r"[^\d]", "", whole)
            fraction_digits = re.sub(r"[^\d]", "", fraction)

            # On exige les 2 chiffres de centimes
            if whole_digits and len(fraction_digits) == 2:
                candidate = f"{whole_digits},{fraction_digits} €"
                if parse_price(candidate) is not None:
                    return candidate
    except Exception:
        pass

    return None


def extract_product_rating(card):
    """
    Récupère la note moyenne du produit (ex: '4,5 sur 5 étoiles').
    POURQUOI LA NOTE PEUT-ELLE ÊTRE VIDE DANS DATA.CSV ?
    Les nouveaux produits récemment mis en vente sur Amazon n'ont pas encore reçu
    d'avis clients : Amazon n'affiche donc aucune étoile sur leur carte.
    """
    selectors = [
        "i.a-icon-star-small span.a-icon-alt",
        'i[data-cy="reviews-ratings-slot"] span.a-icon-alt',
        "span.a-icon-alt",
    ]
    for selector in selectors:
        rating = get_element_text(card, selector)
        if rating and ("étoile" in rating.lower() or "sur 5" in rating.lower()):
            return rating
    return None


def extract_product_seller(card):
    """
    Récupère le nom du vendeur UNIQUEMENT s'il est écrit sur la carte de résultats.
    POURQUOI LA COLONNE 'SELLER' EST-ELLE PRESQUE TOUJOURS VIDE DANS DATA.CSV ?
    Sur les pages de liste de résultats Amazon, Amazon affiche le titre, la photo,
    la note et le prix, mais n'écrit quasiment jamais « Vendu par ... » (cette
    information ne figure qu'à l'intérieur de la page détaillée du produit).
    Comme la consigne interdit d'inventer le vendeur, on laisse None lorsqu'il est absent.
    """
    try:
        spans = card.find_elements(By.TAG_NAME, "span")
        for span in spans:
            text = (span.text or "").strip()
            match = re.match(
                r"^(?:Vendu par|Expédié et vendu par)\s+(.+)$",
                text,
                re.IGNORECASE,
            )
            if match:
                seller = match.group(1).strip(" .")
                if seller:
                    return seller
    except Exception:
        pass
    return None


def extract_product_image(card):
    """
    Récupère l'adresse URL de l'image du produit en vérifiant dans l'ordre :
    1. L'attribut 'src' (image standard)
    2. L'attribut 'data-src' (image chargée de façon différée / lazy-loading)
    3. L'attribut 'srcset' (liste d'images haute définition selon la taille d'écran)
    """
    try:
        images = card.find_elements(By.CSS_SELECTOR, "img.s-image")
        for image_element in images:
            src = image_element.get_attribute("src") or ""
            data_src = image_element.get_attribute("data-src") or ""
            srcset = image_element.get_attribute("srcset") or ""

            image_url = src or data_src
            if not image_url and srcset:
                first_candidate = srcset.split(",")[0].strip()
                if first_candidate:
                    image_url = first_candidate.split()[0]

            if image_url.startswith("https://") or image_url.startswith("http://"):
                return image_url
    except Exception:
        pass
    return None


def go_to_next_page(driver, current_page_number):
    """
    Clique sur le bouton « Suivant » en bas de la page Amazon.
    Retourne False si on est arrivé à la dernière page ou si le bouton est désactivé.
    """
    try:
        next_buttons = driver.find_elements(By.CSS_SELECTOR, "a.s-pagination-next")
        if not next_buttons:
            log_info(f"Page {current_page_number} : bouton « Suivant » absent (dernière page atteinte).")
            return False

        next_button = next_buttons[0]
        disabled = next_button.get_attribute("aria-disabled")
        if disabled == "true":
            log_info(f"Page {current_page_number} : bouton « Suivant » grisé/désactivé (dernière page atteinte).")
            return False

        old_url = driver.current_url
        log_info(f"Navigation de la page {current_page_number} vers la page {current_page_number + 1}...")

        # On fait défiler l'écran jusqu'au bouton Suivant avant de cliquer (comportement humain)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
        time.sleep(0.6)
        next_button.click()

        # On attend que l'adresse URL de la page change
        WebDriverWait(driver, TIMEOUT_SECONDS).until(
            lambda d: d.current_url != old_url
        )

        # On attend que la nouvelle page soit chargée par le navigateur
        WebDriverWait(driver, TIMEOUT_SECONDS).until(
            lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
        )

        if detect_problem_page(driver):
            log_error("Blocage détecté après le clic sur la page suivante.")
            return False

        return True

    except Exception as error:
        log_warning(f"Arrêt de la pagination après la page {current_page_number} : {error}")
        return False


def scrape_amazon_search(keyword, max_pages=3, driver=None):
    """
    Fonction centrale d'extraction :
    1. Ouvre Amazon.fr et passe automatiquement le bouton « Continuer les achats ».
    2. Tape le mot-clé dans la barre de recherche et appuie sur Entrée.
    3. Analyse toutes les cartes produits de chaque page et affiche un diagnostic
       clair lorsqu'un produit n'a pas de prix ou de note sur Amazon.
    """
    own_driver = False
    products = []
    seen_asins = set()
    extraction_errors = 0
    pages_scraped = 0
    blocked = False
    stop_reason = ""

    # Sélecteur CSS qui cible toutes les cartes produit possédant un identifiant ASIN
    cards_selector = 'div[data-component-type="s-search-result"][data-asin]'

    try:
        if driver is None:
            driver = create_stealth_driver()
            own_driver = True

        # ÉTAPE 1 : Ouverture de la page d'accueil Amazon.fr
        log_info(f"Ouverture de {BASE_URL}...")
        driver.get(BASE_URL)
        time.sleep(1.5)

        # Clique automatiquement sur « Continuer les achats » / « Continuer vos achats » et cookies
        click_continue_if_present(driver)

        if detect_problem_page(driver):
            blocked = True
            stop_reason = "Page de blocage détectée dès l'accueil."
            return {
                "products": products,
                "pages_scraped": pages_scraped,
                "errors": extraction_errors + 1,
                "blocked": blocked,
                "stop_reason": stop_reason,
            }

        # ÉTAPE 2 : Saisie du mot-clé dans la barre de recherche
        try:
            search_box = WebDriverWait(driver, TIMEOUT_SECONDS).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "#twotabsearchtextbox"))
            )
        except TimeoutException:
            # Ultime tentative de cliquer sur le bouton intermédiaire s'il est apparu tardivement
            click_continue_if_present(driver)
            try:
                search_box = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "#twotabsearchtextbox"))
                )
            except TimeoutException:
                blocked = detect_problem_page(driver)
                stop_reason = "Champ de recherche '#twotabsearchtextbox' introuvable."
                log_error(stop_reason)
                return {
                    "products": products,
                    "pages_scraped": pages_scraped,
                    "errors": extraction_errors + 1,
                    "blocked": blocked,
                    "stop_reason": stop_reason,
                }

        log_info(f"Recherche du mot-clé : « {keyword} »")
        search_box.clear()
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.ENTER)

        # Attente de l'apparition des premiers résultats
        try:
            WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, cards_selector))
            )
        except TimeoutException:
            blocked = detect_problem_page(driver)
            stop_reason = "Aucune fiche produit visible après la recherche."
            log_error(stop_reason)
            return {
                "products": products,
                "pages_scraped": pages_scraped,
                "errors": extraction_errors + 1,
                "blocked": blocked,
                "stop_reason": stop_reason,
            }

        # ÉTAPE 3 : Boucle sur les pages de résultats (de 1 jusqu'à max_pages)
        for page_number in range(1, max_pages + 1):
            if detect_problem_page(driver):
                blocked = True
                stop_reason = f"Blocage Amazon détecté à la page {page_number}."
                break

            try:
                WebDriverWait(driver, TIMEOUT_SECONDS).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, cards_selector))
                )
            except TimeoutException:
                extraction_errors += 1
                stop_reason = f"Délai dépassé en attendant les fiches de la page {page_number}."
                log_error(stop_reason)
                break

            # Petite pause pour laisser les images et les prix finir de s'afficher
            time.sleep(1.5)
            cards = driver.find_elements(By.CSS_SELECTOR, cards_selector)
            total_cards = len(cards)

            if total_cards == 0:
                stop_reason = f"Aucune fiche détectée à la page {page_number}."
                log_warning(stop_reason)
                break

            pages_scraped += 1
            page_valid_count = 0
            missing_price_count = 0
            missing_rating_count = 0

            for card in cards:
                try:
                    asin = (card.get_attribute("data-asin") or "").strip()
                    # Si la carte n'a pas d'ASIN ou a déjà été vue sur une page précédente, on passe
                    if not asin or asin in seen_asins:
                        continue

                    # 1. NOM DU PRODUIT (Obligatoire : on ignore la carte s'il manque)
                    name = extract_product_name(card)
                    if not name:
                        extraction_errors += 1
                        log_warning(f"Page {page_number} (ASIN {asin}) : nom introuvable, carte ignorée.")
                        continue

                    # 2. URL DU PRODUIT (Obligatoire : on ignore la carte si aucune URL exploitable)
                    product_url = extract_product_url(card, asin)
                    if not product_url:
                        extraction_errors += 1
                        log_warning(f"Page {page_number} (ASIN {asin}) : URL introuvable, carte ignorée.")
                        continue

                    # 3. PRIX DU PRODUIT (Facultatif sur Amazon : None si non affiché ou sans centimes)
                    price_text = extract_product_price(card)
                    if price_text is None:
                        missing_price_count += 1
                        short_name = name[:45] + "..." if len(name) > 45 else name
                        log_diagnostic(
                            asin,
                            f"Prix absent dans data.csv pour « {short_name} » : Amazon n'affiche pas "
                            "de prix direct sur cette carte (choix d'options requis, vendeurs tiers "
                            "uniquement ou rupture temporaire)."
                        )

                    # 4. NOTE DU PRODUIT (Facultatif : None si le produit n'a pas encore d'avis client)
                    rating = extract_product_rating(card)
                    if rating is None:
                        missing_rating_count += 1

                    # 5. VENDEUR (Facultatif : None car rarement affiché sur la page de recherche)
                    seller = extract_product_seller(card)

                    # 6. IMAGE (Facultatif : on tente le téléchargement plus tard)
                    image_url = extract_product_image(card)

                    products.append({
                        "product_id": asin,
                        "name": name,
                        "price_text": price_text,
                        "seller": seller,
                        "rating": rating,
                        "product_url": product_url,
                        "image_url": image_url,
                        "scraped_at": now(),
                    })

                    seen_asins.add(asin)
                    page_valid_count += 1

                except WebDriverException as error:
                    extraction_errors += 1
                    log_error(f"Page {page_number} : erreur Selenium sur une fiche : {error}")
                except Exception as error:
                    extraction_errors += 1
                    log_error(f"Page {page_number} : erreur inattendue sur une fiche : {error}")

            log_success(
                f"Page {page_number}/{max_pages} : {page_valid_count} produit(s) valide(s) retenu(s) "
                f"(dont {missing_price_count} sans prix affiché et {missing_rating_count} sans note client)."
            )

            # Si on a atteint le nombre maximum de pages demandé, on s'arrête
            if page_number >= max_pages:
                stop_reason = "Limite de pages configurée atteinte."
                break

            # ÉTAPE 4 : Passage à la page suivante
            if not go_to_next_page(driver, page_number):
                if detect_problem_page(driver):
                    blocked = True
                stop_reason = f"Fin de pagination après la page {page_number}."
                break

    except (TimeoutException, WebDriverException) as error:
        extraction_errors += 1
        stop_reason = f"Erreur Selenium : {error}"
        log_error(stop_reason)

    except Exception as error:
        extraction_errors += 1
        stop_reason = f"Erreur inattendue : {error}"
        log_error(stop_reason)

    finally:
        # Si cette fonction a créé son propre navigateur, elle le referme proprement
        if own_driver and driver is not None:
            try:
                driver.quit()
                log_info("Navigateur fermé.")
            except WebDriverException:
                pass

    return {
        "products": products,
        "pages_scraped": pages_scraped,
        "errors": extraction_errors,
        "blocked": blocked,
        "stop_reason": stop_reason,
    }


# ==============================================================================
# COUCHE 6 : SERVICE D'EXPORTATION CSV ET BILANS
# ==============================================================================

def export_all(category, subcategory, paths):
    """
    Synchronise les fichiers CSV sur le disque dur à partir du contenu de la base SQLite :
    1. '<categorie>/<sous_categorie>/data.csv'  : Tous les produits de la sous-catégorie.
    2. '<categorie>/<sous_categorie>/recap.csv' : L'historique des exécutions.
    3. '<categorie>/recap.csv'                  : Le résumé global de la catégorie.
    """
    (
        category_dir,
        subcategory_dir,
        images_dir,
        data_file,
        subcategory_recap,
        category_recap,
    ) = paths

    products = get_products(category, subcategory)
    write_csv(data_file, PRODUCT_FIELDS, products)

    runs = get_runs(category, subcategory)
    write_csv(subcategory_recap, RUN_FIELDS, runs)

    category_summary = get_category_summary(category)
    write_csv(category_recap, CATEGORY_SUMMARY_FIELDS, category_summary)


# ==============================================================================
# COUCHE 7 : ORCHESTRATEUR MÉTIER ET POINT D'ENTRÉE (MAIN)
# ==============================================================================

def run_subcategory(category, subcategory, keyword, driver=None):
    """
    Exécute le cycle complet pour une sous-catégorie :
    1. Création des dossiers et fichiers CSV.
    2. Enregistrement du début de l'exécution dans SQLite.
    3. Collecte des produits sur Amazon avec Selenium.
    4. Téléchargement des images et sauvegarde dans SQLite.
    5. Mise à jour des fichiers CSV et affichage du bilan.
    """
    paths = create_directories(category, subcategory)
    images_dir = paths[2]

    run_id = start_run(category, subcategory)

    summary = {
        "end_time": None,
        "pages_scraped": 0,
        "products_found": 0,
        "products_saved": 0,
        "errors": 0,
        "failures": 0,
        "status": "en_cours",
    }

    try:
        result = scrape_amazon_search(
            keyword,
            max_pages=MAX_PAGES_PER_SEARCH,
            driver=driver,
        )

        raw_products = result["products"]
        summary["pages_scraped"] = result["pages_scraped"]
        summary["errors"] += result["errors"]
        if result.get("blocked"):
            summary["errors"] += 1

        summary["products_found"] = len(raw_products)

        log_info(f"Téléchargement des images et enregistrement SQLite pour {len(raw_products)} produits...")

        for item in raw_products:
            try:
                # Conversion du texte du prix en nombre décimal (ou None si pas de prix affiché)
                price = parse_price(item["price_text"])

                # Téléchargement de l'image : si le téléchargement échoue, on garde quand même le produit
                image_path = None
                if item["image_url"]:
                    image_name = f"{create_slug(item['name'])}-{item['product_id']}"
                    image_path = download_image(item["image_url"], images_dir / image_name)
                    if image_path is None:
                        summary["errors"] += 1

                product = {
                    "product_id": item["product_id"],
                    "name": item["name"],
                    "price": price,
                    "currency": "EUR" if price is not None else None,
                    "seller": item["seller"],
                    "rating": item["rating"],
                    "product_url": item["product_url"],
                    "image_path": image_path,
                    "scraped_at": item["scraped_at"],
                    "category": category,
                    "subcategory": subcategory,
                }

                save_product(product)
                summary["products_saved"] += 1

            except Exception as error:
                summary["errors"] += 1
                summary["failures"] += 1
                log_error(f"Erreur d'enregistrement sur le produit {item.get('product_id')} : {error}")

        # Calcul du statut final de l'exécution
        if summary["products_saved"] == 0:
            summary["status"] = "echec"
        elif result.get("blocked") or summary["failures"] > 0 or summary["errors"] > 0:
            summary["status"] = "partiel"
        else:
            summary["status"] = "succes"

    except Exception as error:
        summary["errors"] += 1
        summary["failures"] += 1
        summary["status"] = "echec"
        log_error(f"Scraping interrompu : {error}")

    finally:
        summary["end_time"] = now()
        finish_run(run_id, summary)
        export_all(category, subcategory, paths)

        print("\n" + "=" * 50)
        print(f"BILAN : {category.upper()} > {subcategory.upper()}")
        print("=" * 50)
        print("Pages parcourues     :", summary["pages_scraped"])
        print("Produits trouvés     :", summary["products_found"])
        print("Produits enregistrés :", summary["products_saved"])
        print("Erreurs              :", summary["errors"])
        print("Échecs               :", summary["failures"])
        print("Statut final         :", summary["status"])
        print("=" * 50)


def main():
    """
    Point d'entrée principal du programme.
    ASTUCE ANTI-BOT & PERFORMANCE :
    On ouvre UNE SEULE fenêtre Chrome au début du programme et on la réutilise
    pour toutes les catégories et sous-catégories, exactement comme un humain
    qui fait plusieurs recherches à la suite dans le même onglet !
    """
    init_database()

    driver = None
    try:
        driver = create_stealth_driver()

        for category, subcategories in CATEGORIES.items():
            for subcategory, keyword in subcategories.items():
                print(
                    "\n" + "#" * 60 +
                    f"\n# CATÉGORIE      : {category}"
                    f"\n# SOUS-CATÉGORIE : {subcategory}"
                    f"\n# RECHERCHE      : {keyword}"
                    "\n" + "#" * 60
                )
                run_subcategory(
                    category,
                    subcategory,
                    keyword,
                    driver=driver,
                )
                # Petite pause humaine entre deux recherches différentes
                time.sleep(2.0)

    finally:
        if driver is not None:
            try:
                driver.quit()
                log_info("Session terminée : navigateur Chrome fermé proprement.")
            except WebDriverException:
                pass


# Condition standard en Python : ce bloc ne s'exécute que si on lance directement ce fichier.
if __name__ == "__main__":
    main()


