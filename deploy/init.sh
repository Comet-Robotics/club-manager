script_path=$(realpath "${BASH_SOURCE:-$0}")
echo "The absolute path is $script_path"
BASE_PATH=$(dirname $script_path)
echo "The BASE_PATH is $BASE_PATH"

ln -s $BASE_PATH/gunicorn.service /etc/systemd/system/gunicorn.service
ln -s $BASE_PATH/gunicorn.socket /etc/systemd/system/gunicorn.socket
ln -s $BASE_PATH/discord_bot.service /etc/systemd/system/discord_bot.service
ln -s $BASE_PATH/post_office_queue.service /etc/systemd/system/post_office_queue.service
ln -s $BASE_PATH/post_office_queue.timer /etc/systemd/system/post_office_queue.timer
ln -s $BASE_PATH/post_office_cleanup.service /etc/systemd/system/post_office_cleanup.service
ln -s $BASE_PATH/post_office_cleanup.timer /etc/systemd/system/post_office_cleanup.timer
ln -s $BASE_PATH/clubManager.nginx.conf /etc/nginx/sites-available/clubManager
ln -s /etc/nginx/sites-available/clubManager /etc/nginx/sites-enabled/clubManager


systemctl enable discord_bot.service
systemctl enable gunicorn.socket
systemctl enable gunicorn.service
# The timers are enabled, not the oneshot services they trigger.
systemctl enable post_office_queue.timer
systemctl enable post_office_cleanup.timer

rm /etc/nginx/sites-enabled/default
sudo systemctl daemon-reload