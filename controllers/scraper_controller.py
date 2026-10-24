# ==============================================================================
# CONTRÔLEUR : LE CHEF D'ORCHESTRE
# ==============================================================================
# Le contrôleur relie les MODÈLES (données) et les VUES (affichage / fichiers) :
#   1. il demande au modèle Selenium de collecter les produits ;
#   2. il demande au modèle SQLite de les enregistrer ;
#   3. il demande à la vue de produire les CSV et d'afficher le bilan.
# Il ne contient ni requête SQL, ni sélecteur Selenium, ni mise en forme.
# ==============================================================================

# --- Bibliothèques externes / standards ---
import time                                     # Pour faire des pauses (attendre quelques secondes comme un humain)
from selenium.common.exceptions import (
    WebDriverException,                         # Erreur générale liée au navigateur Chrome
)

# --- Modules du projet ---
from config import CATEGORIES, CATEGORY_SUMMARY_FIELDS, MAX_PAGES_PER_SEARCH, PRODUCT_FIELDS, RUN_FIELDS
from views.csv_view import create_directories, write_csv
from utils.helpers import create_slug, now, parse_price
from models.amazon_scraper import create_stealth_driver, scrape_amazon_search
from models.image_downloader import download_image
from models.database import finish_run, get_category_summary, get_products, get_runs, init_database, save_product, start_run
from utils.logger import log_error, log_info
from views.console_view import print_category_banner, print_summary


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

        print_summary(category, subcategory, summary)


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
                print_category_banner(category, subcategory, keyword)
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
