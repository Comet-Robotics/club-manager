from django.db import models
from django.contrib.auth.models import User
import uuid

class AccountLink(models.Model):
    SOCIAL_CHOICES = (('discord', 'Discord'),('other', 'Other'))

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    link_type = models.CharField(max_length=200, choices=SOCIAL_CHOICES)
    social_id = models.CharField(max_length=200)

    def __str__(self):
        return self.user.first_name