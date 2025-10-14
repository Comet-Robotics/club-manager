from core.models import ServerSettings, User
from django.http import HttpRequest
from django.contrib.auth.models import AnonymousUser
from projects.models import Project
from typing import Iterable, TypedDict


class LayoutData(TypedDict):
    user: User | AnonymousUser
    settings: ServerSettings
    accessible_projects: Iterable[Project]


def get_layout_data(request: HttpRequest) -> LayoutData:
    user = request.user
    if not isinstance(user, (AnonymousUser, User)):
        raise Exception("User must be an instance of User or AnonymousUser")
    accessible_projects = Project.get_projects_user_can_manage(user) if user and isinstance(user, User) else []
    return LayoutData(user=user, settings=ServerSettings.objects.get_or_create()[0], accessible_projects=accessible_projects)
