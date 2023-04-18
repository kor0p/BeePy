from django.shortcuts import render
from django.conf import settings


def index(request):
    return render(request, 'index.html', {'DEBUG': settings.DEBUG})


def custom_url(request):
    return render(request, 'custom_url/index.html')
