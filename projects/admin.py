from django.contrib import admin
from .models import Project, SubTeam, TeamMember

admin.site.register(Project)
admin.site.register(SubTeam)
admin.site.register(TeamMember)
