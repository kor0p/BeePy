from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path
from django.views.decorators.cache import never_cache
from django.views.static import serve

from . import views


def auto_html_serve(*args, **kwargs):
    print(kwargs['path'])
    kwargs['path'] += '/index.html'
    return serve(*args, **kwargs)


if settings.USE_SERVER_SIDE:
    urlpatterns_e = static('/', view=auto_html_serve, document_root=settings.STATICFILES_DIRS[0] / 'dist')
else:
    urlpatterns_e = [re_path('e/.*', views.render_page('index.html'))]

urlpatterns = [
    path('custom_url', views.render_page('custom_url/index.html')),
    path('multiple-apps', views.render_page('multiple_apps/index.html')),
    *urlpatterns_e,
    *static(settings.STATIC_URL, document_root=settings.STATIC_ROOT, show_indexes=True),
]

if settings.IS_DEV:
    urlpatterns = static('BEEPY/', view=never_cache(serve), document_root='../') + urlpatterns
