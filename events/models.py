from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from payments.models import Product, PurchasedProduct


# Create your models here.
class Event(models.Model):
    event_name = models.CharField(max_length=200)
    event_date = models.DateTimeField("event date")
    url = models.CharField(max_length=200, default="https://cometrobotics.org")
    def __str__(self):
        return self.event_name
    
class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    
    def __str__(self):
        return str(self.event) + ' - ' + str(self.timestamp)


class CombatEvent(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='combat_event')
    
    # Documenso is an open source DocuSign clone that we use to store the waivers for minors and adults. It sends an email with a link to the document that they can e-sign (or we can optionally embed that same flow into our project via a React component).
    # If a user's DOB indicates they are under 18, they will receive the minor waiver to sign, which also requires their parent to sign before Documenso will mark it as complete. most of what we found on COPPA said that we should be fine storing minor data as long as we have parental permission which this can cover
    
    robot_combat_events_event_id = models.CharField()
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    def __str__(self):
        return str(self.event)
        
        
class Waiver(models.Model):
      event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='waivers')
      name = models.CharField(max_length=200)
      internal_description = models.CharField(max_length=200)
      alternate_for_waiver_id = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
      minors_must_complete =  models.BooleanField(default=False)
      documenso_id = models.CharField(max_length=200)
      
      def __str__(self):
          return self.name
          
class CompletedWaiver(models.Model):
    waiver = models.ForeignKey(Waiver, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    
    # TODO: how to model a completed waiver? completed waiver could be from documenso, or a paper waiver, or a PDF?
    # to simplify, maybe we scan in paper waivers so we either have a documenso id or a path to a PDF (in an S3 bucket?? or on local disk??? idk django had some nice stuff for this that colin or mason played with)
    
    def __str__(self):
        return str(self.waiver) + ' - ' + str(self.user)
    

class CombatTeam(models.Model):
  robot_combat_events_team_id = models.CharField()
  managers = models.ManyToManyField(User, related_name='managed_teams')
  name = models.CharField(max_length=200)
  
  def __str__(self):
      return self.name
      
class CombatRobot(models.Model):
  robot_combat_events_robot_id = models.CharField()
  combat_team = models.ForeignKey(CombatTeam, on_delete=models.CASCADE)
  purchased_product = models.ForeignKey(PurchasedProduct, on_delete=models.CASCADE)
  
  def __str__(self):
      return self.name
  

class UserIdentification(models.Model):
    # TODO: we should combine the UserProfile and UserIdentification models. this model is redundant since it only has one field
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)

    def create_extended_user(net_id, student_id, first, last):
        user = UserIdentification.create_basic_user(net_id, first, last)
        UserIdentification.objects.create(user=user, student_id=student_id)

    def create_basic_user(net_id, first, last):
        return User.objects.create(username=net_id, first_name=first, last_name=last)

    def link_user(user_id, student_id):
        UserIdentification.objects.create(user=User.objects.get(pk=user_id), student_id=student_id)

    def __str__(self):
        return self.user.first_name + '_' + self.user.last_name + '_' + self.student_id

class Reservation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
    def rsvpBeforeEvent(event, user):
        print("im called")
        reservation = Reservation.objects.filter(event=event, user=user).first()
        if reservation.timestamp < event.event_date:
            return True
        else:
            return False
    
    def __str__(self):
        return str(self.event) + ' - ' + str(self.user)
