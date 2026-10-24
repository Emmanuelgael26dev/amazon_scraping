# ==============================================================================
# MODÈLE : SCRAPER SELENIUM (NAVIGATION HUMAINE & EXTRACTION DU DOM)
# ==============================================================================
# Ce fichier pilote Chrome avec Selenium et extrait les données brutes des
# produits Amazon (nom, prix, note, vendeur, image, URL). Il ne sauvegarde rien
# et n'affiche rien de "mise en forme" : il fournit seulement les données.
# ==============================================================================

# --- Bibliothèques externes / standards ---
import re                                       # Pour utiliser les Expressions Régulières (filtrer du texte)
import time                                     # Pour faire des pauses (attendre quelques secondes comme un humain)
from urllib.parse import urljoin, urlparse, unquote  # Pour analyser, reconstruire et décoder les adresses web (URL)
from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,                           # Erreur déclenchée quand une page met trop de temps à répondre
    WebDriverException,                         # Erreur générale liée au navigateur Chrome
)
from selenium.webdriver.common.by import By     # Permet de cibler un élément HTML (par ID, classe CSS, XPath...)
from selenium.webdriver.common.keys import Keys # Permet de simuler les touches du clavier (comme la touche Entrée)
from selenium.webdriver.support import expected_conditions as EC  # Conditions d'attente (ex: élément visible)
from selenium.webdriver.support.ui import WebDriverWait           # Attente intelligente jusqu'à ce qu'un élément apparaisse

# --- Modules du projet ---
from config import BASE_URL, TIMEOUT_SECONDS
from utils.logger import log_diagnostic, log_error, log_info, log_success, log_warning
from utils.helpers import now, parse_price


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
