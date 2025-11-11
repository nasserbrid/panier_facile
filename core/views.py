
from django.shortcuts import render

def mentions_legales(request):
    return render(request, 'legal/mentions_legales.html')

def rgpd(request):
    return render(request, 'legal/rgpd.html')
