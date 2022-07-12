from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.http.response import HttpResponse

from . import views


urlpatterns = [
    path('', views.index),
    path('__init__.py', lambda *a: HttpResponse()),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
