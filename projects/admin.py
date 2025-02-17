from django.contrib import admin
from .models import Project, Team, TeamMember

admin.site.register(Project)
admin.site.register(Team)
admin.site.register(TeamMember)
