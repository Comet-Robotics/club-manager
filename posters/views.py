from datetime import datetime
from typing import Any
from django.db.models import Count
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.http import HttpRequest, HttpResponse, JsonResponse
from .models import Poster, Visit, Campaign
from .forms import PosterLogForm
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

    data.sort(key=lambda o: o['visits'], reverse=True)

    return JsonResponse(data, safe=False)

@login_required
def show_poster_stats(request):
    return render(request, 'poster_stats.html')

def log_poster(request):
    if request.method == 'POST':
        form = PosterLogForm(request.POST)
        if form.is_valid():
            id = form.cleaned_data['poster_id']
            longitude = form.cleaned_data['longitude']
            latitude = form.cleaned_data['latitude']
            description = form.cleaned_data['description']
            date = datetime.now()
            campaign = Campaign.objects.get(pk=1)
            poster = Poster.objects.update_or_create(pk=id, longitude=longitude,
                                                  latitude=latitude, location=description,
                                                  pub_date=date, campaign=campaign)
            return render(request, 'poster_log.html', {'form': PosterLogForm(), 'message': 'Poster added!'})
    else:
        form = PosterLogForm()
    return render(request, 'poster_log.html', {'form': form})

class PosterListView(ListView):
    model = Poster
    paginate_by = 30

    def get_queryset(self) -> QuerySet[Any]:
        queryset = super().get_queryset()
        return queryset.annotate(visits_count=Count('visits')).filter(visits_count__gt=0).order_by('visits_count')

    # ordering = ['-visits_count']
