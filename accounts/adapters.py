from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import PermissionDenied

class NoSocialLoginAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False  # Prevents signing up with social accounts

class NoSocialLoginSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Prevent login/signup via social account but allow linking
        if not sociallogin.is_existing and not request.user.is_authenticated:
            raise PermissionDenied("Social account login is disabled.")
