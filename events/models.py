from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class Event(models.Model):
    event_name = models.CharField(max_length=200)
    event_date = models.DateTimeField("event date")    
    def __str__(self):
        return self.event_name
    
class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    
    def __str__(self):
        return str(self.event) + ' - ' + str(self.timestamp)
    
class UserIdentification(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    
    def create_extended_user(net_id, student_id, first, last):
        User.objects.create(username=net_id, first_name=first, last_name=last)
        UserIdentification.objects.create(user=User.objects.get(username=net_id), student_id=student_id)
        
    def create_basic_user(net_id, first, last):
        User.objects.create(username=net_id, first_name=first, last_name=last)
    
    def __str__(self):
        return self.user.first_name + '_' + self.user.last_name + '_' + self.student_id

class Reservation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def __str__(self):
        return str(self.event) + ' - ' + str(self.user)