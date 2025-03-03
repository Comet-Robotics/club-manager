from django.urls import path, re_path
from . import views


urlpatterns = [
    path('<int:project_id>/', views.project_view, name='project_view'),
]