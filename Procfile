release: python backend/manage.py migrate
web: gunicorn backend.test_task_django_pyweb.wsgi -b 0.0.0.0:$PORT
