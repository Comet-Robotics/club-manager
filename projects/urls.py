from django.urls import path, re_path
from . import views


urlpatterns = [
    path("<int:project_id>/", views.project_view, name="project_view"),
    path("<int:project_id>/events", views.EventView.as_view(), name="events"),
    path("<int:project_id>/members", views.MembersView.as_view(), name="members"),
    path("team/<int:team_id>/new_member_search", views.NewMemberSearchView.as_view(), name="new_member_search"),
]
