# notes

you'll need to install python 3.11 and [pipenv](https://pipenv.pypa.io/en/latest/#install-pipenv-today) before continuing.

note that for a production deployment, you'll need to install pipenv globally as opposed to just for the current user which is recommended in pipenv docs: `sudo pip install pipenv`

first, install deps and create virtualenv: `pipenv install`

obtain the config.ini from Jason or Mason for Square, place at root of project

run server: `pipenv run python manage.py runserver`
run migrations: `pipenv run python manage.py migrate`
create migrations: `pipenv run python manage.py makemigrations`
run static: `pipenv run python manage.py collectstatic`
create superuser: `pipenv run python manage.py createsuperuser`

to \[re-\]deploy: `./deploy/run.sh`

viewing logs
- `journalctl -u gunicorn.service`
- `journalctl -u gunicorn.socket`
- `journalctl -u discord_bot.service`
