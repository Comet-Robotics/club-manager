from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from payments.models import Product, PurchasedProduct
from common.utils import validate_staff
from computedfields.models import ComputedFieldsModel, computed
from django.utils.translation import gettext_lazy as _
from django.db.models import Q
from projects.models import Project, Team


# Create your models here.
class Event(models.Model):
    event_name = models.CharField(max_length=200)
    event_date = models.DateTimeField("event date")
    url = models.CharField(max_length=200, default="https://cometrobotics.org")

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="events", null=True, blank=True)
    teams = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="events", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.event_name

    def get_attendance(self):
        return self.attendances.all().count()

    def get_attendees(self):
        return self.attendances.all()

    def get_expected_attendees(self):
        if self.teams is not None:
            total_members = (
                User.objects.filter(Q(teams_leading=self.teams) | Q(teams_in=self.teams)).distinct("id").count()
            )
        elif self.project is not None:
            total_members = self.project.all_team_members().count()
        else:
            total_members = None
        return total_members

    def get_attendance_rate(self):
        return (self.get_attendance() / self.get_expected_attendees()) * 100


class Attendance(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendances")
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return str(self.event) + " - " + str(self.timestamp)


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
