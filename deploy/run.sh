pipenv install --deploy
cd frontend && npm install && npm run build && cd ..
pipenv run python manage.py migrate
pipenv run python manage.py collectstatic
sudo systemctl restart gunicorn
sudo systemctl restart discord_bot