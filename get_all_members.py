import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clubManager.settings')
from clubManager import settings

import django
django.setup()

import csv
from django.contrib.auth.models import User

with open('members.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(('LastName', 'FirstName', 'Email'))
    for user in User.objects.all():
        if not user.userprofile.is_member()[1]:
            continue
        writer.writerow((user.last_name, user.first_name, user.username+'@utdallas.edu'))
