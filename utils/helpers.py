# ==============================================================================
# UTILS / HELPERS : FONCTIONS UTILITAIRES (DATE, PRIX, TEXTE)
# ==============================================================================
# Petits outils réutilisables : date du jour, conversion d'un prix texte en
# nombre, création d'un "slug" (nom de fichier propre).
# ==============================================================================

# --- Bibliothèques externes / standards ---
import re                                       # Pour utiliser les Expressions Régulières (filtrer du texte)
from datetime import datetime                   # Pour récupérer la date et l'heure exactes de la collecte
from decimal import Decimal, InvalidOperation   # Pour manipuler les prix avec précision sans erreurs d'arrondi


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
