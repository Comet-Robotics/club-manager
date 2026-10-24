from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

from common.utils import normalize_username

UserModel = get_user_model()


class CaseInsensitiveModelBackend(ModelBackend):
    """
    Authenticate on the canonical username, case-insensitively.

    The lookup is ``iexact`` on the normalized input rather than an exact match on the
    lowercased value, so logins keep working for rows the backfill has not rewritten yet
    (e.g. a deploy where the new code serves before migration 0030 runs). The migration and
    the unique index guarantee a single match going forward; if two rows still collide, this
    refuses to guess between them.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None
        username = normalize_username(username)
        if not username:
            return None
        try:
            user = UserModel._default_manager.get(username__iexact=username)
        except UserModel.DoesNotExist:
            # Same timing-attack mitigation as ModelBackend: run the hasher once so a
            # missing user costs about as much as a password check.
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            UserModel().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
