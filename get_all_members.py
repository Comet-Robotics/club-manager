import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clubManager.settings")
from clubManager import settings

import django

django.setup()

import csv
from core.models import UserProfile

with open("members.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(("LastName", "FirstName", "Email"))
    for user in UserProfile.get_active_members():
        writer.writerow((user.last_name, user.first_name, user.username + "@utdallas.edu"))
