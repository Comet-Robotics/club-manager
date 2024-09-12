from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver

from payments.models import Payment, Term

# Create your models here.
class UserProfile(models.Model):
    GENDER_CHOICES = (('M', 'Male'),('F', 'Female'),('O', 'Other'))

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    discord_id = models.CharField(max_length=200, null=True, blank=True, unique=True)

    def __str__(self):
        return self.user.first_name + '_' + self.user.last_name
    
    def is_member(self, for_term: Term | None = None) -> tuple[Term, Payment | None]:
        """
        Returns a tuple with the Term and Payment object for the current member if the user is a member for the given term, or a tuple with the given Term and None if they are not a member.
        """
        if for_term:
            term = for_term
        else:
            term = Term.objects.filter(start_date__lte=models.functions.Now(), end_date__gte=models.functions.Now()).first()
            if not term:
                raise Exception("No current Term found.")

        payment = Payment.objects.filter(user=self.user, product=term.product, is_successful=True)

        return term, payment.first()
    
    def apply_discord_roles(self, dry_run=False): 
        roles_to_apply = []
        if self.is_member()[1]:
            pass
            




@receiver(post_save, sender=User)
def update_profile_signal(sender, instance, created, **kwargs):
    # if created:
    if created or not hasattr(instance, "userprofile"):
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()
