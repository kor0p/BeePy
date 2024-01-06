from django.shortcuts import render
from django.conf import settings


def render_page(page):
    def _page(request):
        return render(request, page, {'IS_DEV': settings.IS_DEV})

    return _page
