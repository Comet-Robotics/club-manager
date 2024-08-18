from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path('<int:poster_id>/', views.log_and_redirect, name='log_and_redirect'),
    path('stats/poster-data/', views.poster_stats, name='poster_stats' ),
    path('stats/', views.PosterListView.as_view(), name='show_poster_stats'),
    path('log-poster/', views.log_poster, name='log_poster'),
]