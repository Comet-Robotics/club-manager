from allauth.socialaccount import signals
from allauth.socialaccount.models import SocialAccount
from django.http import HttpRequest

def delete_social_account(request: HttpRequest, provider: str):
  account = SocialAccount.objects.get(provider=provider, user=request.user)
  if not account:
    raise Exception(f"No account found for provider: {provider}")
  account.delete()
  signals.social_account_removed.send(sender=SocialAccount,
                                      request=request,
                                      socialaccount=account)
