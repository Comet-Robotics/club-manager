from datetime import datetime
from django.core.management.base import BaseCommand, CommandError

from clubManager import settings

NGINX_TEMPLATE_PATH = settings.BASE_DIR / "deploy" / "clubManager.nginx.conf.template"
NGINX_OUTPUT_PATH = settings.BASE_DIR / "deploy" / "clubManager.nginx.conf"


class Command(BaseCommand):
    help = "Fills in the Nginx configuration template to generate a Nginx configuration based on current settings."

    def handle(self, *args, **options):
        replacements = {
            "${MEDIA_PATH}": settings.MEDIA_ROOT.absolute().as_posix(),
        }

        try:
            with open(NGINX_TEMPLATE_PATH, "r") as template_file:
                nginx_config = template_file.read()

                for placeholder, actual in replacements.items():
                    nginx_config = nginx_config.replace(placeholder, actual)

            with open(NGINX_OUTPUT_PATH, "w") as output_file:
                output_file.write(
                    "# WARNING: This file is auto-generated. Do not edit directly as changes will be overwritten on next deploy. To make changes to the Nginx config that will persist longer than this deployment, edit `deploy/clubManager.nginx.conf.template`, then run `pipenv run python manage.py generate_nginx_configuration` to regenerate the file.\n"
                )

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                output_file.write(f"# Generated on {now}\n\n")
                output_file.write(nginx_config)

            self.stdout.write(self.style.SUCCESS(f"Nginx configuration generated at {NGINX_OUTPUT_PATH}"))
        except Exception as e:
            raise CommandError(f"Error generating Nginx configuration: {e}")
