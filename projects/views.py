from datetime import timedelta, datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django_tables2 import SingleTableView
from core.utilities import get_layout_data
from events.models import Event
from django.http import Http404
from django.views.generic import ListView

from projects.tables import EventTable

# Used to get all the current events in a given time window. Ex: If it is now 3pm on a Monday, and the delta is set to 4 hours, we should see all events starting from 11am (3pm - 4 hours) and 7pm (3pm + 4 hours.)
CURRENT_EVENT_WINDOW = timedelta(hours=4)


class EventView(SingleTableView):
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
