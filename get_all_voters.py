import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clubManager.settings")
from clubManager import settings

import django

django.setup()

import csv
from datetime import datetime
from events.models import Attendance
from django.contrib.auth.models import User

MIN_ATTENDANCES = 3
ATTENDANCES_SINCE = datetime(2025, 1, 1)

with open("voters.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(("FirstName", "LastName", "Email"))
    for user in User.objects.all():
        if not user.userprofile.is_member()[1]:
            continue
        attendances = Attendance.objects.filter(user=user, event__event_date__gt=ATTENDANCES_SINCE)
        if len(attendances) >= MIN_ATTENDANCES:
            writer.writerow((user.first_name, user.last_name, user.username + "@utdallas.edu"))
