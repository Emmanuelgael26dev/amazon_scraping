# ==============================================================================
# MODÈLE : BASE DE DONNÉES SQLITE
# ==============================================================================
# Ce fichier gère TOUT ce qui touche à la base de données db.sqlite :
# création des tables, sauvegarde des produits (sans doublons), historique
# des exécutions, lecture des données. Le reste du programme ne parle jamais
# directement à SQLite : il passe par ces fonctions.
# ==============================================================================

# --- Bibliothèques externes / standards ---
import sqlite3                                  # Pour gérer la base de données locale SQLite sans serveur externe

# --- Modules du projet ---
from config import DB_PATH
from utils.helpers import now


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
