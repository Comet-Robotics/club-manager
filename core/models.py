from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from clubManager import settings
from common.major import get_majors, get_major_from_netid
from payments.models import Payment, PurchasedProduct, Term
import discord

# Create your models here.
class UserProfile(models.Model):
    class GenderChoice(models.TextChoices):
        MALE = 'M', _('Male')
        FEMALE = 'F', _('Female')
        OTHER = 'O', _('Other')

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    gender = models.CharField(max_length=1, choices=GenderChoice.choices, null=True, blank=True)
    discord_id = models.CharField(max_length=200, null=True, blank=True, unique=True)
    major = models.CharField(choices=list(get_majors().items())+[("unknown", "Unknown")], null=True, blank=True, default=None)  # NULL indicates major needs to be fetched
    is_utd_affiliate = models.BooleanField(null=False, blank=False, default=True) # TODO: get rid of default=True and fix UserProfile creation with null field
    date_of_birth = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user.first_name + '_' + self.user.last_name
    
    def is_member(self, for_term: Term | None = None) -> tuple[Term, PurchasedProduct | None]:
        """
        Returns a tuple with the Term and PurchasedProduct object for the current member if the user is a member for the given term, or a tuple with the given Term and None if they are not a member.
        """
        if for_term:
            term = for_term
        else:
            term = Term.get_current_term()
            if not term:
                raise Exception("No current Term found.")

        purchased_product = PurchasedProduct.objects.filter(payment__user=self.user, product=term.product, payment__is_successful=True)

        return term, purchased_product.first()
    
    def apply_discord_roles(self, dry_run=False): 
        roles_to_apply: list[int] = []
        if self.is_member()[1]:
            roles_to_apply.append(settings.DISCORD_MEMBER_ROLE_ID)

        if not dry_run:
            client = discord.Client()
            # TODO apply roles

        return roles_to_apply


@receiver(post_save, sender=User)
def update_user_signal(sender, instance, created, **kwargs):
    # if created:
    if created or not hasattr(instance, "userprofile"):
        UserProfile.objects.create(user=instance)
    instance.userprofile.save()

@receiver(post_save, sender=UserProfile)
def update_profile_signal(sender, instance, created, **kwargs):
    if not instance.is_utd_affiliate:
        return
    if created or instance.major is None:
        instance.major = get_major_from_netid(instance.user.username) or "unknown"
        instance.save()
