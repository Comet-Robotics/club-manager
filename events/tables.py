import django_tables2 as tables
from django.contrib.auth.models import User
from django_tables2.utils import A
from .models import UserIdentification

class UserTable(tables.Table):    
    student_id = tables.Column(accessor='useridentification.student_id', verbose_name='Student ID')
    
    def __init__(self, *args, event_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_id = event_id
    
    sign_in = tables.TemplateColumn("""
            <a style="color: red"href="{% url 'pass_sign_in' table.event_id record.id %}">Sign-In</a>
    """, orderable=False)
    
    class Meta:
        model = User
        fields = ("first_name", "last_name", "username")
        
class LinkUserTable(tables.Table):    
    student_id = tables.Column(accessor='useridentification.student_id', verbose_name='Student ID')
    
    def __init__(self, *args, event_id=None, student_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.student_id = student_id
        self.event_id = event_id
    
    sign_in = tables.TemplateColumn("""
            <a style="color: red"href="{% url 'pass_link' table.event_id record.id table.student_id  %}">Link User</a>
    """, orderable=False)
    
    class Meta:
        model = User
        fields = ("first_name", "last_name", "username")