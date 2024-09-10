# notes

you'll need to install python 3.11 and [pipenv](https://pipenv.pypa.io/en/latest/#install-pipenv-today) before continuing.

first, install deps and create virtualenv: `pipenv install`

obtain the config.ini from Jason or Mason for Square

run server: `pipenv run python manage.py runserver`
run migrations: `pipenv run python manage.py migrate`
create migrations: `pipenv run python manage.py makemigrations`
run static: `pipenv run python manage.py collectstatic`
create superuser: `pipenv run python manage.py createsuperuser`

to redeploy: `git switch main && git pull && pipenv install && pipenv run python manage.py migrate && pipenv run python manage.py collectstatic && sudo systemctl restart gunicorn`

TODO: Update systemd services to use pipenv, copy systemd service files and nginx config from server to repo for reproducibility
