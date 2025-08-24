from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from payments.models import Product


# Create your models here.
class Event(models.Model):
    event_name = models.CharField(max_length=200)
    event_date = models.DateTimeField("event date")
    url = models.CharField(max_length=200, default="https://cometrobotics.org")

    def __str__(self):
        return self.event_name


class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendances")
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return str(self.event) + " - " + str(self.timestamp)


class CombatEvent(models.Model):
    # SUGGESTION (to consider when I am not sleep deprived): instead of creating a CombatEvent model, add models for EventWith Waivers, EventWithPayments, EventWithRobotCombatEvents, etc.

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="combat_events")
    # Documenso is an open source DocuSign clone that we use to store the waivers for minors and adults. It sends an email with a link to the document that they can e-sign (or we can optionally embed that same flow into our project via a React component).
    # If a user's DOB indicates they are under 18, they will receive the minor waiver to sign, which also requires their parent to sign before Documenso will mark it as complete. most of what we found on COPPA said that we should be fine storing minor data as long as we have parental permission which this can cover
    documenso_minor_waiver_id = models.CharField()
    documenso_adult_waiver_id = models.CharField()
    robot_combat_events_event_id = models.CharField()
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.event)


class CombatEventRegistration(models.Model):
    combat_event = models.ForeignKey(CombatEvent, on_delete=models.CASCADE)
    robot_combat_events_robot_id = models.CharField()

    # TODO: add other RCE fields (robot name, etc)

    # TODO figure out payments. this is more complex than it seems since a user can register multiple robots
    # but right now the payment models make a 1:1 association between a payment and a product, so
    # a user would have to go through the payment process multiple times to register multiple robots.
    # We can solve this in 2 ways: add a quantity field to the payment model (easiest but least flexible) or
    # change the payment models (a lot). A payment would no longer be directly tied to a single product ID. A payment now be associated with another table PaymentProducts that has a foreign key to the Product table and a quantity field. The Payment amount_cents would be the sum of the product prices for all the products in the PaymentProducts table and whatever service fee Square adds.
    #
    # The migration for this would be annoying but doable. This is definitely a better solution but not my focus anymore so committing this rn and switching focus to forms that allow non-UTD users to pay for stuff.


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
        return self.user.first_name + "_" + self.user.last_name + "_" + self.student_id


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
        return str(self.event) + " - " + str(self.user)
