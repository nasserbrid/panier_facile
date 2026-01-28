"""
Vues pour la géolocalisation.
"""
import json
import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def save_temp_location(request):
    """
    Sauvegarde temporairement la localisation de l'utilisateur.
    """
    from django.contrib.gis.geos import Point

    try:
        data = json.loads(request.body)
        latitude = float(data.get('latitude'))
        longitude = float(data.get('longitude'))
        address = data.get('address', '')

        if data.get('save_to_profile', False):
            request.user.location = Point(longitude, latitude, srid=4326)
            request.user.address = address
            request.user.save()

        request.session['temp_location'] = {
            'latitude': latitude,
            'longitude': longitude,
            'address': address
        }

        return JsonResponse({
            'success': True,
            'message': 'Localisation enregistrée avec succès'
        })

    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
