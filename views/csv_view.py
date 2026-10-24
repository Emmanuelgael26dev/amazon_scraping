# ==============================================================================
# VUE : SORTIE CSV (data.csv, recap.csv) ET DOSSIERS DE RÉSULTATS
# ==============================================================================
# La "vue" est ce que l'utilisateur obtient en sortie du programme. Ici :
# les fichiers CSV et l'arborescence de dossiers qui les contient.
# ==============================================================================

# --- Bibliothèques externes / standards ---
import csv                                      # Pour lire et écrire des fichiers tabulaires .csv
from pathlib import Path                        # Pour gérer les chemins de dossiers sur Windows, Mac et Linux

# --- Modules du projet ---
from config import CATEGORY_SUMMARY_FIELDS, PRODUCT_FIELDS, ROOT, RUN_FIELDS


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
