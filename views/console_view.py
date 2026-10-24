# ==============================================================================
# VUE : AFFICHAGE DANS LE TERMINAL (EN-TÊTES ET BILANS)
# ==============================================================================


def print_category_banner(category, subcategory, keyword):
    """Affiche l'en-tête d'une recherche (catégorie, sous-catégorie, mot clé)."""
    print(
        "\n" + "#" * 60 +
        f"\n# CATÉGORIE      : {category}"
        f"\n# SOUS-CATÉGORIE : {subcategory}"
        f"\n# RECHERCHE      : {keyword}"
        "\n" + "#" * 60
    )


def print_summary(category, subcategory, summary):
    """Affiche le bilan final d'une sous-catégorie dans le terminal."""
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
