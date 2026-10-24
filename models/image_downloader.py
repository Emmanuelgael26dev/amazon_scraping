# ==============================================================================
# MODÈLE : TÉLÉCHARGEMENT DES IMAGES PRODUIT
# ==============================================================================

# --- Bibliothèques externes / standards ---
import mimetypes                                # Pour deviner l'extension d'une image (.jpg, .png) selon son type
from pathlib import Path                        # Pour gérer les chemins de dossiers sur Windows, Mac et Linux
from urllib.request import Request, urlopen     # Pour télécharger les fichiers images depuis Internet

# --- Modules du projet ---
from config import ROOT
from utils.logger import log_warning


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
