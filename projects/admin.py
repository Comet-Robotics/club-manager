from django.contrib import admin
from .models import Project, Subteam, TeamMember

admin.site.register(Project)
admin.site.register(Subteam)
admin.site.register(TeamMember)
