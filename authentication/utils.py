"""
Utilitaires pour la géolocalisation et la recherche de commerces.
"""
import requests
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class OverpassAPI:
    """
    Client pour interroger l'API Overpass d'OpenStreetMap.
    Permet de trouver des commerces à proximité d'une position GPS.
    """

    OVERPASS_URL = "https://overpass-api.de/api/interpreter"

    # Types de commerces recherchés
    SHOP_TYPES = {
        'supermarket': 'Supermarché',
        'convenience': 'Épicerie',
        'butcher': 'Boucherie',
        'deli': 'Charcuterie',
        'greengrocer': 'Primeur',
        'bakery': 'Boulangerie',
        'grocery': 'Épicerie',
    }

    @classmethod
    def find_intermarche_stores(
        cls,
        latitude: float,
        longitude: float,
        radius: int = 5000
    ) -> List[Dict]:
        """
        Recherche spécifiquement les magasins Intermarché à proximité.
        Utilise Nominatim pour des performances optimales.

        Args:
            latitude: Latitude du point de recherche
            longitude: Longitude du point de recherche
            radius: Rayon de recherche en mètres (par défaut 5km)

        Returns:
            Liste de dictionnaires contenant les informations des magasins Intermarché
        """
        # Utiliser directement Nominatim (plus rapide et fiable qu'Overpass)
        return cls._find_intermarche_via_nominatim(latitude, longitude, radius)

    @classmethod
    def _find_intermarche_via_nominatim(
        cls,
        latitude: float,
        longitude: float,
        radius: int = 5000
    ) -> List[Dict]:
        """Recherche Intermarché via Nominatim (fallback)."""
        try:
            # Recherche via Nominatim
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'format': 'json',
                'q': 'Intermarché',
                'bounded': 1,
                'viewbox': f"{longitude - 0.05},{latitude - 0.05},{longitude + 0.05},{latitude + 0.05}",
                'limit': 20
            }
            headers = {
                'User-Agent': 'PanierFacile/1.0'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            stores = []
            for item in data:
                try:
                    store_lat = float(item['lat'])
                    store_lon = float(item['lon'])
                    distance = cls._calculate_distance(latitude, longitude, store_lat, store_lon)

                    # Filtrer par rayon
                    if distance <= radius:
                        stores.append({
                            'id': item.get('osm_id', 0),
                            'name': item.get('display_name', 'Intermarché').split(',')[0],
                            'type': 'supermarket',
                            'type_label': 'Supermarché',
                            'latitude': store_lat,
                            'longitude': store_lon,
                            'address': item.get('display_name', ''),
                            'distance': distance,
                            'distance_text': cls._format_distance(distance),
                            'phone': '',
                            'website': '',
                            'opening_hours': '',
                            'osm_url': f"https://www.openstreetmap.org/{item.get('osm_type', 'node')}/{item.get('osm_id', 0)}"
                        })
                except (ValueError, KeyError) as e:
                    logger.debug(f"Erreur parsing Nominatim: {e}")
                    continue

            stores.sort(key=lambda x: x['distance'])
            logger.info(f"Nominatim: Trouvé {len(stores)} magasins Intermarché dans un rayon de {radius/1000}km")
            return stores

        except Exception as e:
            logger.error(f"Erreur Nominatim fallback: {e}")
            return []

    @classmethod
    def find_carrefour_stores(
        cls,
        latitude: float,
        longitude: float,
        radius: int = 5000
    ) -> List[Dict]:
        """
        Recherche spécifiquement les magasins Carrefour à proximité.

        Args:
            latitude: Latitude du point de recherche
            longitude: Longitude du point de recherche
            radius: Rayon de recherche en mètres (par défaut 5km)

        Returns:
            Liste de dictionnaires contenant les informations des magasins Carrefour
        """
        return cls._find_retailer_via_nominatim('Carrefour', latitude, longitude, radius)

    @classmethod
    def find_auchan_stores(
        cls,
        latitude: float,
        longitude: float,
        radius: int = 5000
    ) -> List[Dict]:
        """
        Recherche spécifiquement les magasins Auchan à proximité.

        Args:
            latitude: Latitude du point de recherche
            longitude: Longitude du point de recherche
            radius: Rayon de recherche en mètres (par défaut 5km)

        Returns:
            Liste de dictionnaires contenant les informations des magasins Auchan
        """
        return cls._find_retailer_via_nominatim('Auchan', latitude, longitude, radius)

    @classmethod
    def _find_retailer_via_nominatim(
        cls,
        retailer_name: str,
        latitude: float,
        longitude: float,
        radius: int = 5000
    ) -> List[Dict]:
        """
        Méthode générique pour rechercher une enseigne via Nominatim.

        Args:
            retailer_name: Nom de l'enseigne (Carrefour, Auchan, etc.)
            latitude: Latitude du point de recherche
            longitude: Longitude du point de recherche
            radius: Rayon de recherche en mètres

        Returns:
            Liste de dictionnaires contenant les informations des magasins
        """
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'format': 'json',
                'q': retailer_name,
                'bounded': 1,
                'viewbox': f"{longitude - 0.05},{latitude - 0.05},{longitude + 0.05},{latitude + 0.05}",
                'limit': 20
            }
            headers = {
                'User-Agent': 'PanierFacile/1.0'
            }

            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()

            stores = []
            for item in data:
                try:
                    store_lat = float(item['lat'])
                    store_lon = float(item['lon'])
                    distance = cls._calculate_distance(latitude, longitude, store_lat, store_lon)

                    # Filtrer par rayon
                    if distance <= radius:
                        stores.append({
                            'id': item.get('osm_id', 0),
                            'name': item.get('display_name', retailer_name).split(',')[0],
                            'type': 'supermarket',
                            'type_label': 'Supermarché',
                            'latitude': store_lat,
                            'longitude': store_lon,
                            'address': item.get('display_name', ''),
                            'distance': distance,
                            'distance_text': cls._format_distance(distance),
                            'phone': '',
                            'website': '',
                            'opening_hours': '',
                            'osm_url': f"https://www.openstreetmap.org/{item.get('osm_type', 'node')}/{item.get('osm_id', 0)}"
                        })
                except (ValueError, KeyError) as e:
                    logger.debug(f"Erreur parsing Nominatim {retailer_name}: {e}")
                    continue

            stores.sort(key=lambda x: x['distance'])
            logger.info(f"Nominatim: Trouvé {len(stores)} magasins {retailer_name} dans un rayon de {radius/1000}km")
            return stores

        except Exception as e:
            logger.error(f"Erreur Nominatim {retailer_name}: {e}")
            return []

    @classmethod
    def find_nearby_stores(
        cls,
        latitude: float,
        longitude: float,
        radius: int = 2000,
        shop_types: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Recherche les commerces à proximité d'une position GPS.

        Args:
            latitude: Latitude du point de recherche
            longitude: Longitude du point de recherche
            radius: Rayon de recherche en mètres (par défaut 2km)
            shop_types: Liste des types de commerces à rechercher
                       (si None, recherche tous les types définis)

        Returns:
            Liste de dictionnaires contenant les informations des commerces
        """
        if shop_types is None:
            shop_types = list(cls.SHOP_TYPES.keys())

        # Construire la requête Overpass QL
        shop_filters = '|'.join(shop_types)
        query = f"""
        [out:json][timeout:25];
        (
          node["shop"~"^({shop_filters})$"](around:{radius},{latitude},{longitude});
          way["shop"~"^({shop_filters})$"](around:{radius},{latitude},{longitude});
        );
        out center tags;
        """

        try:
            response = requests.post(
                cls.OVERPASS_URL,
                data={'data': query},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            stores = []
            for element in data.get('elements', []):
                store = cls._parse_store_element(element, latitude, longitude)
                if store:
                    stores.append(store)

            # Trier par distance
            stores.sort(key=lambda x: x['distance'])

            return stores

        except requests.RequestException as e:
            logger.error(f"Erreur lors de la requête Overpass: {e}")
            return []
        except Exception as e:
            logger.error(f"Erreur lors du traitement des données: {e}")
            return []

    @classmethod
    def _parse_store_element(
        cls,
        element: Dict,
        user_lat: float,
        user_lon: float
    ) -> Optional[Dict]:
        """
        Parse un élément OSM pour extraire les informations du commerce.

        Args:
            element: Élément OSM (node ou way)
            user_lat: Latitude de l'utilisateur (pour calculer la distance)
            user_lon: Longitude de l'utilisateur

        Returns:
            Dictionnaire avec les informations du commerce ou None
        """
        tags = element.get('tags', {})

        # Récupérer les coordonnées
        if element['type'] == 'node':
            lat = element.get('lat')
            lon = element.get('lon')
        elif element['type'] == 'way':
            center = element.get('center', {})
            lat = center.get('lat')
            lon = center.get('lon')
        else:
            return None

        if not lat or not lon:
            return None

        # Récupérer les informations
        shop_type = tags.get('shop', 'unknown')
        name = tags.get('name', f"{cls.SHOP_TYPES.get(shop_type, 'Commerce')} sans nom")

        # Adresse
        address_parts = []
        if tags.get('addr:housenumber'):
            address_parts.append(tags['addr:housenumber'])
        if tags.get('addr:street'):
            address_parts.append(tags['addr:street'])
        if tags.get('addr:city'):
            address_parts.append(tags['addr:city'])

        address = ', '.join(address_parts) if address_parts else 'Adresse non disponible'

        # Calculer la distance
        distance = cls._calculate_distance(user_lat, user_lon, lat, lon)

        # Téléphone
        phone = tags.get('phone', tags.get('contact:phone', ''))

        # Site web
        website = tags.get('website', tags.get('contact:website', ''))

        # Horaires d'ouverture
        opening_hours = tags.get('opening_hours', '')

        return {
            'id': element['id'],
            'name': name,
            'type': shop_type,
            'type_label': cls.SHOP_TYPES.get(shop_type, shop_type.title()),
            'latitude': lat,
            'longitude': lon,
            'address': address,
            'distance': distance,
            'distance_text': cls._format_distance(distance),
            'phone': phone,
            'website': website,
            'opening_hours': opening_hours,
            'osm_url': f"https://www.openstreetmap.org/{element['type']}/{element['id']}"
        }

    @staticmethod
    def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calcule la distance en mètres entre deux points GPS (formule de Haversine).

        Args:
            lat1, lon1: Coordonnées du premier point
            lat2, lon2: Coordonnées du second point

        Returns:
            Distance en mètres
        """
        from math import radians, sin, cos, sqrt, atan2

        R = 6371000  # Rayon de la Terre en mètres

        lat1_rad = radians(lat1)
        lat2_rad = radians(lat2)
        delta_lat = radians(lat2 - lat1)
        delta_lon = radians(lon2 - lon1)

        a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        distance = R * c
        return round(distance, 2)

    @staticmethod
    def _format_distance(distance: float) -> str:
        """
        Formate une distance en mètres pour un affichage lisible.

        Args:
            distance: Distance en mètres

        Returns:
            Texte formaté (ex: "250 m" ou "1.5 km")
        """
        if distance < 1000:
            return f"{int(distance)} m"
        else:
            return f"{distance / 1000:.1f} km"
