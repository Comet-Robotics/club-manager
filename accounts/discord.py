"""
Lookups against Discord's HTTP API for the web side of the app.

This lives outside `accounts.views` so that `accounts.models` can describe a pending
Discord link when it writes a registration email. Views already import models, so the
helper cannot stay there without making that import cycle.
"""

from typing import TypedDict

import requests

from clubManager import settings

# Nothing here is on the critical path of a page: a slow or unreachable Discord should
# degrade to "we could not look this up" rather than hold a request open until Gunicorn
# gives up on the worker.
DISCORD_API_TIMEOUT_SECONDS = 5


class DiscordUser(TypedDict):
    username: str
    discord_id: int
    profile_image: str


def get_discord_user(user_id: int, bot_token: str) -> DiscordUser | None:
    url = f"https://discord.com/api/v10/users/{user_id}"
    headers = {"Authorization": f"Bot {bot_token}"}

    response = requests.get(url, headers=headers, timeout=DISCORD_API_TIMEOUT_SECONDS)

    if not response.status_code == 200:
        return None

    user_data = response.json()

    discord_id = int(user_data["id"])
    discriminator = int(user_data["discriminator"]) or 0

    if "avatar" in user_data:
        profile_image = f"https://cdn.discordapp.com/avatars/{discord_id}/{user_data['avatar']}.png"
    else:
        discord_profile_image_index = ((discord_id >> 22) % 6) if discriminator == 0 else discriminator % 5
        profile_image = f"https://cdn.discordapp.com/embed/avatars/{discord_id}.png"

    return {"username": user_data["username"], "discord_id": discord_id, "profile_image": profile_image}


def describe_discord_user(discord_id: str) -> DiscordUser | None:
    """
    Who a Discord ID belongs to, or `None` if we cannot say.

    Used to name a Discord account to the person being asked to approve it, which is a
    nicety rather than a requirement: the ID is shown either way. Deliberately never
    raises, so a missing bot token or a Discord outage cannot stop a registration email
    going out or a registration page rendering.
    """
    # settings.py runs the environment variable through `str()`, so an unconfigured
    # deployment arrives here as the literal string "None" rather than an empty one.
    bot_token = (settings.DISCORD_TOKEN or "").strip()
    if not bot_token or bot_token == "None":
        return None

    try:
        return get_discord_user(int(discord_id), bot_token)
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return None
