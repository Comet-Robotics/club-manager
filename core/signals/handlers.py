from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import sync_to_async

from common.major import get_major_from_netid
from core.models import UserProfile
from payments.models import Payment

import aiohttp

async def add_member_role(discord_id: int):
    async with aiohttp.request("POST", "http://localhost:2468/give-member-role", json={"member_id": discord_id}) as resp:
        return await resp.json()

@receiver(post_save, sender=UserProfile)
async def update_roles_profile_signal(sender, instance: UserProfile, created, **kwargs):
    def is_member():
        return instance.is_member()[1]
    valid = sync_to_async(is_member)()
    if (discord_id:=instance.discord_id) and valid:
        await add_member_role(int(discord_id))

@receiver(post_save, sender=Payment)
async def update_roles_payment_signal(sender, instance: Payment, created, **kwargs):
    def is_member():
        return instance.user.userprofile.is_member()[1]
    valid = sync_to_async(is_member)()
    if (discord_id:=instance.user.userprofile.discord_id) and valid:
        await add_member_role(int(discord_id))


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
