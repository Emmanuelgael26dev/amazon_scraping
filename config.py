# ==============================================================================
# CONFIG.PY : TOUS LES RÉGLAGES DU PROJET AU MÊME ENDROIT
# ==============================================================================
# Si tu veux changer une catégorie, le nombre de pages ou un chemin, tu modifies
# UNIQUEMENT ce fichier. Aucun autre fichier ne contient de réglage "en dur".
# ==============================================================================

# --- Bibliothèques externes / standards ---
from pathlib import Path                        # Pour gérer les chemins de dossiers sur Windows, Mac et Linux


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
