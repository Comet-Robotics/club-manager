from datetime import timedelta, datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django_tables2 import SingleTableView
from core.utilities import get_layout_data
from events.models import Event
from django.http import Http404
from django.contrib.auth.models import User
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Q

from projects.tables import EventTable, MemberTable
from projects.models import Project

from django_tables2 import MultiTableMixin
from django.views.generic.base import TemplateView
from projects.models import Team

# Used to get all the current events in a given time window. Ex: If it is now 3pm on a Monday, and the delta is set to 4 hours, we should see all events starting from 11am (3pm - 4 hours) and 7pm (3pm + 4 hours.)
CURRENT_EVENT_WINDOW = timedelta(hours=4)


class CanManageProjectMixin(UserPassesTestMixin):
    def test_func(self):
        project_id = self.kwargs["project_id"]
        project = Project.objects.get(pk=project_id)

        return Project.user_can_manage_project(self.request.user, project)


class CanManageTeamMixin(UserPassesTestMixin):
    def test_func(self):
        team_id = self.kwargs["team_id"]
        team = Team.objects.get(pk=team_id)
        print(team)
        return Team.user_can_manage_team(self.request.user, team)


class EventView(CanManageProjectMixin, SingleTableView):
    table_class = EventTable
    model = Event
    template_name = "project_events.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = context | get_layout_data(self.request)
        return context

    def get_queryset(self):
        project_id = self.kwargs["project_id"]
        return Event.objects.filter(project_id=project_id)


class NewMemberSearchView(CanManageTeamMixin, SingleTableView):
    template_name = "add_member_to_team.html"
    table_class = MemberTable
    model = User

    def get_queryset(self):
        team_id = self.kwargs["team_id"]
        search = self.request.GET.get("search", "")
        team = Team.objects.get(pk=team_id)
        filter = Q()
        if search:
            filter = Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
        return User.objects.filter(filter).difference(team.get_unique_users())


class MembersView(CanManageProjectMixin, MultiTableMixin, TemplateView):
    model = User
    template_name = "project_members.html"

    def get_tables(self, *args, **kwargs):
        project_id = self.kwargs.get("project_id")
        project = Project.objects.get(pk=project_id)
        teams = project.all_teams()

        tables = [MemberTable(team.get_unique_users(), table_name=team.name, team_id=team.id) for team in teams]
        return tables

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context = context | get_layout_data(self.request)
        return context


@login_required
def project_view(request, project_id):
    layout_data = get_layout_data(request)
    project = next((p for p in layout_data["accessible_projects"] if p.id == project_id), None)

    if not project:
        raise Http404()

    now = datetime.now()
    lower_bound = now - CURRENT_EVENT_WINDOW
    upper_bound = now + CURRENT_EVENT_WINDOW

    current_events = Event.objects.filter(project=project_id, event_date__gt=lower_bound, event_date__lt=upper_bound)
    teams = project.all_teams()

    return render(request, "project_home.html", {**layout_data, "current_events": current_events, "teams": teams})
