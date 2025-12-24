"""
Client API pour l'intégration Intermarché Drive.

Ce module fournit une interface pour interagir avec les APIs Intermarché:
- API Stores: Recherche de magasins
- API Products: Recherche et détails de produits
- API Carts: Gestion des paniers anonymes
"""

import logging
import requests
from typing import List, Dict, Any, Optional
from django.conf import settings
from datetime import datetime
import uuid
import os
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class IntermarcheAPIException(Exception):
    """Exception personnalisée pour les erreurs API Intermarché."""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)


class IntermarcheAPIClient:
    """
    Client pour l'API Intermarché Partner.

    Ce client gère l'authentification et les appels vers les différentes
    APIs Intermarché (Stores, Products, Carts).
    """

    BASE_URL = os.getenv("BASE_URL")

    def __init__(self):
        """
        Initialise le client API avec les credentials depuis les settings.
        """
        self.api_key = settings.INTERMARCHE_API_KEY
        self.app_name = settings.INTERMARCHE_APP_NAME
        self.app_version = settings.INTERMARCHE_APP_VERSION

        if not self.api_key:
            raise IntermarcheAPIException("INTERMARCHE_API_KEY not configured in settings")

    def _get_headers(self) -> Dict[str, str]:
        """
        Retourne les headers d'authentification pour les requêtes API.

        Returns:
            Dict contenant les headers X-Api-Key, X-App-Name, X-App-Version
        """
        return {
            "X-Api-Key": self.api_key,
            "X-App-Name": self.app_name,
            "X-App-Version": self.app_version,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: int = 10
    ) -> Dict[str, Any]:
        """
        Effectue une requête HTTP vers l'API Intermarché.

        Args:
            method: Méthode HTTP (GET, POST, DELETE, etc.)
            endpoint: Endpoint de l'API (ex: "/stores/v1/stores")
            params: Paramètres de query string
            json_data: Corps de la requête JSON
            timeout: Timeout en secondes

        Returns:
            Réponse JSON de l'API

        Raises:
            IntermarcheAPIException: En cas d'erreur API
        """
        url = f"{self.BASE_URL}{endpoint}"
        headers = self._get_headers()

        try:
            logger.debug(f"API Request: {method} {url}")
            logger.debug(f"Params: {params}")
            logger.debug(f"JSON: {json_data}")

            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=timeout
            )

            logger.debug(f"API Response: {response.status_code}")

            # Gestion des erreurs HTTP
            if response.status_code >= 400:
                error_message = f"API Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', error_message)
                except:
                    error_message = response.text or error_message

                logger.error(f"API Error: {error_message}")
                raise IntermarcheAPIException(
                    message=error_message,
                    status_code=response.status_code,
                    response_data=error_data if 'error_data' in locals() else None
                )

            # Retourne la réponse JSON
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"API Timeout: {url}")
            raise IntermarcheAPIException("Request timeout")
        except requests.exceptions.ConnectionError:
            logger.error(f"API Connection Error: {url}")
            raise IntermarcheAPIException("Connection error")
        except requests.exceptions.RequestException as e:
            logger.error(f"API Request Exception: {str(e)}")
            raise IntermarcheAPIException(f"Request failed: {str(e)}")

    # ========== API STORES ==========

    def find_stores_near_location(
        self,
        latitude: float,
        longitude: float,
        distance: int = 5000,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Trouve les magasins Intermarché proches d'une localisation GPS.

        Args:
            latitude: Latitude GPS (ex: 48.8566)
            longitude: Longitude GPS (ex: 2.3522)
            distance: Distance de recherche en mètres (défaut: 5000m = 5km)
            limit: Nombre maximum de résultats (défaut: 10)

        Returns:
            Liste de magasins avec leurs détails (id, nom, adresse, distance, etc.)

        Example:
            >>> client = IntermarcheAPIClient()
            >>> stores = client.find_stores_near_location(48.8566, 2.3522, distance=5000)
            >>> print(stores[0]['name'])
            'INTERMARCHE SUPER PARIS'
        """
        params = {
            "lat": latitude,
            "lon": longitude,
            "distance": distance,
            "limit": limit,
            "ecommerce": "true"  # Filtre uniquement les magasins avec Drive
        }

        response = self._make_request("GET", "/stores/v1/stores", params=params)
        return response.get('stores', [])

    # ========== API PRODUCTS ==========

    def search_products(
        self,
        store_id: str,
        keyword: str,
        page: int = 1,
        size: int = 10,
        tri: str = "PERTINENCE",
        ordre_tri: str = "CROISSANT",
        catalog: List[str] = None
    ) -> Dict[str, Any]:
        """
        Recherche des produits dans un magasin Intermarché.

        Args:
            store_id: ID du magasin (ex: "08177")
            keyword: Mot-clé de recherche (ex: "tomate")
            page: Numéro de page (défaut: 1)
            size: Nombre de résultats par page (défaut: 10)
            tri: Tri des résultats - "PERTINENCE", "PRIX", "NOUVEAUTE" (défaut: "PERTINENCE")
            ordre_tri: Ordre - "CROISSANT" ou "DECROISSANT" (défaut: "CROISSANT")
            catalog: Liste des catalogues - ["pdv"] pour produits du magasin (défaut: ["pdv"])

        Returns:
            Dict contenant:
            - products: Liste des produits trouvés
            - pagination: Infos de pagination
            - aggregations: Facettes de filtrage

        Example:
            >>> result = client.search_products("08177", "tomate")
            >>> for product in result['products']:
            ...     print(f"{product['label']} - {product['price']}€")
        """
        if catalog is None:
            catalog = ["pdv"]

        endpoint = f"/produits/v1/pdvs/{store_id}/produits/search"

        json_data = {
            "keyword": keyword,
            "page": page,
            "size": size,
            "tri": tri,
            "ordreTri": ordre_tri,
            "catalog": catalog
        }

        response = self._make_request("POST", endpoint, json_data=json_data)
        return response

    def get_product_details(
        self,
        store_id: str,
        product_id: str,
        extensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Récupère les détails complets d'un produit.

        Args:
            store_id: ID du magasin
            product_id: ID du produit
            extensions: Extensions de données à inclure
                       ["nutrition", "ingredients", "allergens", "labels"]

        Returns:
            Dict avec toutes les informations du produit

        Example:
            >>> details = client.get_product_details("08177", "12345")
            >>> print(details['label'])
            >>> print(details['price']['value'])
        """
        endpoint = f"/produits/v1/pdvs/{store_id}/produits/{product_id}"

        params = {}
        if extensions:
            params['extensions'] = ','.join(extensions)

        response = self._make_request("GET", endpoint, params=params)
        return response

    def get_categories(self, store_id: str) -> List[Dict[str, Any]]:
        """
        Récupère l'arbre des catégories de produits pour un magasin.

        Args:
            store_id: ID du magasin

        Returns:
            Liste des catégories avec sous-catégories
        """
        endpoint = f"/produits/v1/pdvs/{store_id}/categories"
        response = self._make_request("GET", endpoint)
        return response.get('categories', [])

    # ========== API CARTS ==========

    def create_cart(
        self,
        store_id: str,
        items: List[Dict[str, Any]],
        anonymous_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crée ou synchronise un panier anonyme sur Intermarché Drive.

        Args:
            store_id: ID du magasin (ex: "08177")
            items: Liste des items à ajouter au panier
                   Chaque item doit contenir:
                   - itemId: ID du produit
                   - quantity: Quantité (entier)
                   - catalog: "PDV" (optionnel, défaut: "PDV")
            anonymous_id: UUID du panier anonyme (généré si non fourni)

        Returns:
            Dict contenant:
            - cartId: ID du panier créé
            - items: Items dans le panier
            - totalAmount: Montant total
            - anonymousId: UUID du panier anonyme

        Example:
            >>> items = [
            ...     {"itemId": "12345", "quantity": 2},
            ...     {"itemId": "67890", "quantity": 1}
            ... ]
            >>> cart = client.create_cart("08177", items)
            >>> print(f"Panier créé: {cart['cartId']}")
        """
        if not anonymous_id:
            anonymous_id = str(uuid.uuid4())

        endpoint = "/v1/carts/synchronize"

        params = {
            "storeId": store_id,
            "anonymousId": anonymous_id,
            "isActiveAnonymousPersistence": "true"
        }

        # Construire les événements pour chaque item
        customer_datetime = datetime.now().astimezone().isoformat()
        events = []

        for item in items:
            event = {
                "type": "QUANTITY",
                "catalog": item.get("catalog", "PDV"),
                "dateTime": customer_datetime,
                "itemId": str(item["itemId"]),
                "quantity": int(item["quantity"])
            }
            events.append(event)

        json_data = {
            "customerDateTime": customer_datetime,
            "events": events
        }

        response = self._make_request("POST", endpoint, params=params, json_data=json_data)

        # Ajouter l'anonymousId dans la réponse pour référence
        response['anonymousId'] = anonymous_id

        return response

    def delete_cart(self, cart_id: str, seller_id: Optional[str] = None) -> bool:
        """
        Supprime un panier.

        Args:
            cart_id: ID du panier à supprimer
            seller_id: ID du vendeur (optionnel)

        Returns:
            True si la suppression a réussi

        Example:
            >>> client.delete_cart("abc123")
            True
        """
        endpoint = f"/v1/carts/{cart_id}"

        params = {}
        if seller_id:
            params['sellerId'] = seller_id

        try:
            self._make_request("DELETE", endpoint, params=params)
            return True
        except IntermarcheAPIException as e:
            if e.status_code == 404:
                logger.warning(f"Cart {cart_id} not found")
                return True  # Le panier n'existe plus, considéré comme succès
            raise
