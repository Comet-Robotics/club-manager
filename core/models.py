from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

# Create your models here.
class UserProfile(models.Model):
    GENDER_CHOICES = (('M', 'Male'),('F', 'Female'),('O', 'Other'))

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    discord_id = models.CharField(max_length=200, null=True, blank=True, unique=True)

    def __str__(self):
        return self.user.first_name + '_' + self.user.last_name


@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
    # if created:
    if created or not hasattr(instance, "userprofile"):
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()
