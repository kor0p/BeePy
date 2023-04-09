from django.shortcuts import render
from .utils import IS_DEV


def index(request):
    return render(request, 'index.html', {'IS_DEV': IS_DEV})


def custom_url(request):
    return render(request, 'custom_url/index.html')
