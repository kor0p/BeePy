from django.shortcuts import render
from .utils import IS_DEV


def index(request):
    return render(request, 'test_admin/index.html', {'IS_DEV': IS_DEV})
