pipenv install --deploy
pushd frontend
npm install && npm run build
popd
pipenv run python manage.py migrate
pipenv run python manage.py collectstatic
sudo systemctl restart gunicorn
sudo systemctl restart discord_bot