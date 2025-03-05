from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from core.models import ServerSettings, User
from events.models import Event
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser
from projects.models import Project
from typing import Iterable, TypedDict
from django.conf import settings



class LayoutData(TypedDict):
    user: User | AnonymousUser
    settings: ServerSettings
    accessible_projects: Iterable[Project]

def get_layout_data(request: HttpRequest) -> LayoutData:
    user = request.user
    if not isinstance(user, (AnonymousUser, User)):
        raise Exception("User must be an instance of User or AnonymousUser")
    # NOTE: temporarily hiding these sidebar links in production until the corresponding pages are implemented
    accessible_projects = Project.get_projects_user_can_manage(user) if user and isinstance(user, User) and settings.DEBUG else []
    return LayoutData(user=user, settings=ServerSettings.objects.get(), accessible_projects=accessible_projects)

# Create your views here.
@login_required
def project_view(request, project_id):
    user = request.user
    layout_data = get_layout_data(request)
    
    current_event = Event.objects.filter(project=project_id).order_by('event_date').first()
    teams = Project.objects.get(pk=project_id).all_teams()
    
    return render(request, 'project_home.html', {**layout_data, "current_event": current_event, "teams": teams})