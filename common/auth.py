from django.contrib.auth.backends import ModelBackend

from common.utils import normalize_username


class CaseInsensitiveModelBackend(ModelBackend):
    """
    Authenticate on the canonical lowercase username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is not None:
            kwargs["username"] = normalize_username(username)
        return super().authenticate(request, password=password, **kwargs)
