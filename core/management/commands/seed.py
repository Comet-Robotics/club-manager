from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from projects.models import Project, Team
import seed


PASSWORD = "j"
SEEDED_OBJECT_NAME_PREFIX = "Seeded:"


class Command(BaseCommand):
    help = "Seeds the database with test data."

    def handle(self, *args, **options):
        seed.create_test_data()
