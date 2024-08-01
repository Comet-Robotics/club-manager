import django_tables2 as tables
from django.contrib.auth.models import User
from django_tables2.utils import A
from .models import UserIdentification

class UserTable(tables.Table):
    
    student_id = tables.Column(accessor='useridentification.student_id', verbose_name='Student ID')
    sign_in = tables.TemplateColumn("""
            <a style="color: red"href="{% url 'create-profile' record.id %}">Sign-In</a>
    """, orderable=False)
    
    class Meta:
        model = User
        fields = ("first_name", "last_name", "username")