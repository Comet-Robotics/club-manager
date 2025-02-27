from typing import Iterable, TypedDict
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.views.decorators.http import require_GET
from django.conf import settings
from events.models import Attendance
from django.views.generic import ListView
from core.models import ServerSettings
from core.forms import ServerSettingsForm
from projects.models import Project
from projects.models import Team
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.auth.decorators import user_passes_test


def initials(name: str) -> str:
    split = name.split(' ')
    out = ''
    for i in range(len(split)):
        is_number = split[i].isnumeric()
        is_year = is_number and len(split[i]) == 4
        if is_year:
            out += split[i][-2:]
        elif is_number:
            out += split[i]
        else:
            out += split[i][0]
    return out.upper()

class LayoutData(TypedDict):
    user: User | AnonymousUser
    settings: ServerSettings
    accessible_projects: Iterable[Project]

def get_layout_data(request: HttpRequest) -> LayoutData:
    user = request.user
    if not isinstance(user, (AnonymousUser, User)):
        raise Exception("User must be an instance of User or AnonymousUser")
    settings = ServerSettings.objects.get()
    accessible_projects = Project.get_projects_user_can_manage(user) if user and isinstance(user, User) else []
    return LayoutData(user=user, settings=settings, accessible_projects=accessible_projects)

@login_required
def profile_view(request):
    layout_data = get_layout_data(request)
    teams = Team.get_teams_associated_with_user(request.user)
    terms = [term for term, purchased_product in request.user.userprofile.get_membership_terms()]
    formatted_terms = [initials(term.name) for term in terms]
    return render(request, 'profile.html', {**layout_data, "teams": teams, "terms": formatted_terms})

@login_required
def account_view(request):
    layout_data = get_layout_data(request)
    return render(request, 'account.html', {**layout_data})

@user_passes_test(lambda u:u.is_superuser)
def server_settings_view(request):
    layout_data = get_layout_data(request)
    if request.method == 'POST':
        form = ServerSettingsForm(request.POST, instance=layout_data["settings"])
        if form.is_valid():
            form.save()
    else:
        form = ServerSettingsForm(instance=layout_data["settings"])
    return render(request, 'server_settings.html', {**layout_data,'form': form})

class AttendanceListView(ListView):
    model = Attendance
    template_name = 'profile_fragments/attendance_list.html'
    paginate_by = 5
    context_object_name = 'attendances'
    
    def get_queryset(self):
        return Attendance.objects.order_by('-timestamp').filter(user=self.request.user)

def spa_view(request):
    return render(request, 'spa.html', {'DEBUG': settings.DEBUG})

@require_GET
def apple_merchant_id(request):
    return HttpResponse(settings.SQUARE_APPLE_MERCHANT_ID, content_type="text/plain")

def index(request):
    return HttpResponsePermanentRedirect('/_/')
