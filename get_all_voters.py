import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "clubManager.settings")
from clubManager import settings

import django

django.setup()

import csv
from datetime import datetime
from django.db.models import Count
from events.models import Attendance
from core.models import UserProfile

MIN_ATTENDANCES = 3
ATTENDANCES_SINCE = datetime(2025, 1, 1)

# Voters must be active members who also clear the attendance bar. Both filters are applied as
# queryset lookups rather than per-user loops so the export stays a fixed number of queries.
voter_ids = (
    Attendance.objects.filter(event__event_date__gt=ATTENDANCES_SINCE)
    .values("user_id")
    .annotate(attendance_count=Count("id"))
    .filter(attendance_count__gte=MIN_ATTENDANCES)
    .values_list("user_id", flat=True)
)

with open("voters.csv", "w") as f:
    writer = csv.writer(f)
    writer.writerow(("FirstName", "LastName", "Email"))
    for user in UserProfile.get_active_members().filter(pk__in=voter_ids):
        writer.writerow((user.first_name, user.last_name, user.username + "@utdallas.edu"))
