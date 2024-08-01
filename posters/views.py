from typing import Any
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import HttpRequest, HttpResponse, JsonResponse
from .models import Poster, Visit
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView



def index(request):
    return render(request, 'posters/index.html')

def log_and_redirect(request: HttpRequest, poster_id: int) -> HttpResponse:
    poster = get_object_or_404(Poster, id=poster_id)
    
    visit = Visit(
        poster=poster,
        timestamp=timezone.now(),
    )
    visit.save()
    
    return redirect(poster.campaign.destination_url)

def poster_stats(request: HttpRequest) -> JsonResponse:
    posters = Poster.objects.all()
    data = []

    for poster in posters:
        visits_count = poster.visits.count()
        data.append({
            'latitude': poster.latitude,
            'longitude': poster.longitude,
            'visits': visits_count
        })

    return JsonResponse(data, safe=False)

@login_required
def show_poster_stats(request):
    return render(request, 'poster_stats.html')

class PosterListView(ListView):
    model = Poster
    paginate_by = 30
    
