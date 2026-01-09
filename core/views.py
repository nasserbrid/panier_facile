
from django.shortcuts import render
from django.http import HttpResponse
from django.conf import settings
import os

def mentions_legales(request):
    return render(request, 'legal/mentions_legales.html')

def rgpd(request):
    return render(request, 'legal/rgpd.html')

def cgu(request):
    return render(request, 'legal/cgu.html')

def service_worker(request):
    """
    Servir le Service Worker depuis la racine pour avoir le bon scope (/)
    """
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    with open(sw_path, 'r', encoding='utf-8') as f:
        sw_content = f.read()

    response = HttpResponse(sw_content, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response

def manifest(request):
    """
    Servir le manifest.json depuis la racine avec chemins dynamiques des icônes
    """
    response = render(request, 'pwa/manifest.json', content_type='application/manifest+json')
    return response
