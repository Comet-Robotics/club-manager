from django.shortcuts import render
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.views.decorators.http import require_GET
from django.conf import settings

# Create your views here.
def profile_view(request):
    user = request.user
    return render(request, 'profile.html', {'user': user})

def spa_view(request):
    return render(request, 'spa.html', {'DEBUG': settings.DEBUG})

@require_GET
def apple_merchant_id(request):
    return HttpResponse(settings.SQUARE_APPLE_MERCHANT_ID, content_type="text/plain")

def index(request):
    return HttpResponsePermanentRedirect('/_/')
