from asgiref.sync import sync_to_async

from core.models import User, UserProfile

__all__ = ["get_user_async", "get_profile_async", "get_or_create_profile_async"]


def get_user(**kwargs):
    try:
        return User.objects.get(**kwargs)
    except:
        return None


get_user_async = sync_to_async(get_user)



def get_profile(**kwargs):
    try:
        return UserProfile.objects.get(**kwargs)
    except:
        return None


get_profile_async = sync_to_async(get_profile)



def get_or_create_profile(**kwargs):
    try:
        return UserProfile.objects.get_or_create(**kwargs)[0]
    except Exception as e:
        import traceback

        traceback.print_exc(e)
        return None


get_or_create_profile_async = sync_to_async(get_or_create_profile)
