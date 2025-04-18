# clubManager

clubManager is a web app for managing all things related to club operations. Some of the things it does include:

- Link shortener
- Event check-ins / meeting attendance tracking
- Payment system for member dues and other ad-hoc payments (ex: club shirts), backed by Square
- Discord role management based on membership status
- Discord bot as an alternative interface for some of the above features

## dev setup 
needs to be fleshed out, the deployment section will probably be helpful

first, install deps and create virtualenv: `pipenv install`
obtain the config.ini from Jason or Mason for Square, place at root of project

## deployment

### first time setup
you'll need to install python 3.11 (preferably via [pyenv](http://github.com/pyenv/pyenv?tab=readme-ov-file)), [pipenv](https://pipenv.pypa.io/en/latest/#install-pipenv-today), [nodejs](https://nodejs.org/en) (preferably via [nvm](http://github.com/nvm-sh/nvm?tab=readme-ov-file)), nginx, and postgresql before continuing. this assumes you are deploying on some debian-based system.

for a production deployment, you'll need to install pipenv globally as opposed to just for the current user which is recommended in pipenv docs: `sudo apt install pipenv`. this is so that the pipenv binary is accessible in the systemd services.

once pipenv is installed, run `./deploy/init.sh` (sets up systemd services, does not start them).

### useful commands
- run server: `pipenv run python manage.py runserver`
- run migrations: `pipenv run python manage.py migrate`
- create migrations: `pipenv run python manage.py makemigrations`
- run static: `pipenv run python manage.py collectstatic`
- create superuser: `pipenv run python manage.py createsuperuser`

to \[re-\]deploy: `./deploy/run.sh` (does not include pulling from git)

#### viewing logs
- `journalctl -e -u gunicorn.service`
- `journalctl -e -u gunicorn.socket`
- `journalctl -e -u discord_bot.service`

