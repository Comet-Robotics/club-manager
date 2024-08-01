from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
    GENDER_CHOICES = (('M', 'Male'),('F', 'Female'),('O', 'Other'))
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    def __str__(self):
        return self.user.first_name + '_' + self.user.last_name
