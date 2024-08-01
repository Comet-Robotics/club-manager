from django.db import models
from django.utils import timezone

class Campaign(models.Model):
    campaign_name = models.CharField(max_length=200)
    destination_url = models.URLField(max_length=200, default='/')
    pub_date = models.DateTimeField("date published")
    
    def __str__(self):
        return self.campaign_name

class Poster(models.Model):
    pub_date = models.DateTimeField("date published")
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='posters')
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    location = models.CharField(max_length=200)
    
    def __str__(self):
        return str(self.campaign) + ' - ' + self.location
    

class Visit(models.Model):
    poster = models.ForeignKey(Poster, on_delete=models.CASCADE, related_name='visits')
    timestamp = models.DateTimeField(default=timezone.now)

    