from django.db import models
from django.contrib.auth.models import User
import uuid

class AccountLink(models.Model):
    SOCIAL_CHOICES = (('discord', 'Discord'),('other', 'Other'))

    uuid = models.UUIDField("UUID", default=uuid.uuid4, editable=False, unique=True, primary_key=True)
    date_created = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    link_type = models.CharField(max_length=200, choices=SOCIAL_CHOICES)
    social_id = models.CharField(max_length=200)

    def __str__(self):
        return self.user.first_name
