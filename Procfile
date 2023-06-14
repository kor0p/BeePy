release: cd backend && python manage.py migrate
web: cd backend && gunicorn beepy_webapp.wsgi -b 0.0.0.0:$PORT
