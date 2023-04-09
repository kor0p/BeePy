from django.urls import re_path, path
from django.conf import settings
from django.conf.urls.static import static

from . import views


urlpatterns = [
    path('custom_url', views.custom_url),
    re_path('e/.*', views.index),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT, show_indexes=True)
