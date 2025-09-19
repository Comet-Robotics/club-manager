import django_tables2 as tables
from events.models import Event
from django.contrib.auth.models import User


class EventTable(tables.Table):
    table_title = ""

    class Meta:
        model = Event
        exclude = ("url", "project", "id", "created_at", "updated_at")

    view = tables.TemplateColumn(
        '<a class="button button-primary" href="{%url "event_overview" record.id %}">Overview</a>',
        orderable=False,
        verbose_name="",
    )


class MemberTable(tables.Table):
    # TODO: Implement this
    # delete = tables.TemplateColumn(
    #     '<a class="button button-outline" href="{% url "edit_form" record.id %}">Edit</a>',
    #     orderable=False,
    # )

    class Meta:
        model = User
        # TODO: Show roles in the table
        fields = ("id", "username", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        self.table_name = kwargs.pop("table_name", None)
        self.team_id = kwargs.pop("team_id", None)
        super().__init__(*args, **kwargs)
