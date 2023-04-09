from django.urls import re_path
from django.conf import settings
from django.conf.urls.static import static

from . import views


urlpatterns = [
    re_path('custom_url', views.custom_url),
    re_path('.*', views.index),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT, show_indexes=True)
