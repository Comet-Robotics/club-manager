from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from clubManager import settings

from common.major import get_major_from_netid
from core.models import UserProfile
from payments.models import PurchasedProduct

import aiohttp
from asgiref.sync import sync_to_async


async def add_member_role(discord_id: int):
    async with aiohttp.request(
        "POST",
        "http://localhost:2468/give-member-role",
        json={"member_id": discord_id},
        headers={"Authorization": f"Bearer {settings.API_SECRET}"},
    ) as resp:
        return await resp.json()


@receiver(post_save, sender=UserProfile)
async def update_roles_profile_signal(sender, instance: UserProfile, created, **kwargs):
    def is_member():
        if not (discord_id := instance.discord_id):
            return False, None
        return instance.is_member()[1] is not None, discord_id

    valid, discord_id = await sync_to_async(is_member)()
    if valid:
        await add_member_role(int(discord_id))


@receiver(post_save, sender=PurchasedProduct)
async def update_roles_purchasedproduct_signal(sender, instance: PurchasedProduct, created, **kwargs):
    def is_member():
        if not (discord_id := instance.payment.user.userprofile.discord_id):
            return False, None
        return instance.payment.user.userprofile.is_member()[1] is not None, discord_id

    valid, discord_id = await sync_to_async(is_member)()
    if valid:
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
