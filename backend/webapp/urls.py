from django.urls import re_path, path
from django.conf import settings
from django.conf.urls.static import static

from . import views


urlpatterns = [
    path('custom_url', views.render_page('custom_url/index.html')),
    path('multiple-apps', views.render_page('multiple_apps/index.html')),
    re_path('e/.*', views.render_page('index.html')),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT, show_indexes=True)

if settings.IS_DEV:
    urlpatterns = static('PYWEB/', document_root='../') + urlpatterns
