# ==============================================================================
# UTILS / LOGGER : AFFICHAGE DES MESSAGES DANS LE TERMINAL
# ==============================================================================
# Petites fonctions d'affichage utilisées par TOUTES les couches (modèles,
# contrôleur...). Elles sont ici, dans "utils", car elles ne sont pas liées à
# une couche en particulier.
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
