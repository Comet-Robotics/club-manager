from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from payments.models import Product, PurchasedProduct
from common.utils import validate_staff
from computedfields.models import ComputedFieldsModel, computed
from django.utils.translation import gettext_lazy as _


# Create your models here.
class Event(models.Model):
    event_name = models.CharField(max_length=200)
    event_date = models.DateTimeField("event date")
    url = models.CharField(max_length=200, default="https://cometrobotics.org")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.event_name
    
class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attendances')
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    
    def __str__(self):
        return str(self.event) + ' - ' + str(self.timestamp)


class CombatEvent(models.Model):
    """
    A CombatEvent is an object representing a combat event. This is used to track robot payments and competitor waivers for each event.
    """
    
    event = models.OneToOneField(Event, on_delete=models.CASCADE, related_name='combat_event')
    
    # Documenso is an open source DocuSign clone that we use to store the waivers for minors and adults. It sends an email with a link to the document that they can e-sign (or we can optionally embed that same flow into our project via a React component).
    # If a user's DOB indicates they are under 18, they will receive the minor waiver to sign, which also requires their parent to sign before Documenso will mark it as complete. most of what we found on COPPA said that we should be fine storing minor data as long as we have parental permission which this can cover
    
    robot_combat_events_event_id = models.CharField()
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return str(self.event)
        
        
class Waiver(models.Model):
      """
      A Waiver is an object representing a waiver that can be signed by a user. 
      """
    
      combat_event = models.ForeignKey(CombatEvent, on_delete=models.CASCADE, related_name='waivers')
      name = models.CharField(max_length=200)
      internal_description = models.CharField(max_length=200)
      alternate_for_waiver_id = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)
      is_alternate_waiver_for_minors =  models.BooleanField(default=False)
      documenso_id = models.CharField(max_length=200)
      
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
      
      def __str__(self):
          return self.name
          
class WaiverStatus(ComputedFieldsModel):
    """
    A WaiverStatus is an object tracking whether a "competitor" (someone who is a owner of a robot which is associated with an event) has signed a given waiver associated with that event. 
    
    A waiver is signed if:
    
    - a file is uploaded
    - documenso_id is not null (TODO: documenso id for a waiver status could exist but the waiver may not actually be completed yet. need to track this separately i think)
    - an officer has verified that a user has signed a waiver (fallback for many use-cases, like completing a physical waiver in person, so the completed waiver is not tracked in Documenso or available as a PDF. an internal note should be added to the waiver status to track this)
    """
  
    waiver = models.ForeignKey(Waiver, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='waiver_statuses')
    timestamp = models.DateTimeField(default=timezone.now)

    internal_notes = models.TextField(null=True, blank=True)

    signature_verified_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, validators=[validate_staff], related_name='signature_verifications')
    documenso_id = models.CharField(max_length=200, null=True, blank=True)
    signed_file = models.FileField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    @computed(models.BooleanField(), depends=[('self', ['signed_file', 'documenso_id', 'signature_verified_by'])])
    def is_signed(self):
        return self.signed_file is not None or self.documenso_id is not None or self.signature_verified_by is not None
    
    
    def __str__(self):
        return str(self.waiver) + ' - ' + str(self.user)
    

class CombatTeam(models.Model):
  robot_combat_events_team_id = models.CharField()
  managers = models.ManyToManyField(User, related_name='managed_teams')
  name = models.CharField(max_length=200)
  
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  
  def __str__(self):
      return self.name
    
      
class CombatRobot(models.Model):
  class WeightClass(models.TextChoices):
    PLANT = 'plant', _('Plastic Ant (1lb)')
    ANT = 'ant', _('Antweight (3lb)')
    BEETLE = 'beetle', _('Beetleweight (1lb)')
    
  robot_combat_events_robot_id = models.CharField()
  combat_team = models.ForeignKey(CombatTeam, on_delete=models.CASCADE)
  purchased_products = models.ManyToManyField(PurchasedProduct, related_name='combat_robots', blank=True)
  events = models.ManyToManyField(CombatEvent, related_name='combat_robots')
  owners = models.ManyToManyField(User, related_name='combat_robots')
  name = models.CharField(max_length=200)
  weight_class = models.CharField(choices=WeightClass.choices)
  
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)
  
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
