release: cd backend && python manage.py migrate
web: cd backend && gunicorn test_task_django_pyweb.wsgi -b 0.0.0.0:$PORT
