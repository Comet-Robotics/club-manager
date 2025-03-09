import django_tables2 as tables
from events.models import Event

class EventTable(tables.Table):
    class Meta:
        model = Event
        template_name = "django_tables2/bootstrap.html"
        exclude = ("url", "project", "id", "created_at", "updated_at")
    
    view = tables.TemplateColumn(
        '<a style="color: red" href="{%url "event_overview" record.id %}">Overview</a>',
        orderable=False,
    )