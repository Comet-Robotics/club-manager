# notes 

run server: `python manage.py runserver`
run migrations: `python manage.py migrate`
create migrations: `python manage.py makemigrations`
run static: `python manage.py collectstatic`
create superuser: `python manage.py createsuperuser`

to redeploy: `git switch main && git pull && python manage.py migrate && python manage.py collectstatic && sudo systemctl restart gunicorn`