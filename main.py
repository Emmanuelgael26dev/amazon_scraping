# ==============================================================================
# MAIN.PY : POINT D'ENTRÉE DU PROGRAMME
# ==============================================================================
# Pour lancer le scraper :   python main.py
# Toute la logique est dans controllers/, models/ et views/.
# ==============================================================================

from controllers.scraper_controller import main

# Ce bloc ne s'exécute que si on lance directement ce fichier.
if __name__ == "__main__":
    main()
