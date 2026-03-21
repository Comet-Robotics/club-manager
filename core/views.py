from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET
from django.views.generic import ListView

from core.models import ServerSettings
from core.utilities import get_layout_data
from events.models import Attendance
from projects.models import Team

from .forms import ServerSettingsForm, ServerSettingsLogoForm, UserForm, UserProfileForm


def initials(name: str) -> str:
    split = name.split(" ")
    out = ""
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


@login_required
def profile_view(request, user_id=None):
    layout_data = get_layout_data(request)
    user: User = request.user

    if user_id and (request.user.is_staff or request.user.is_superuser or user_id == request.user.id):
        user = User.objects.get(pk=user_id)
        if not user:
            return HttpResponse("User not found", status=404)

    teams = Team.get_teams_associated_with_user(user)
    terms = [term for term, _ in user.userprofile.get_membership_terms()]
    formatted_terms = [initials(term.name) for term in terms]

    return render(
        request, "profile.html", {**layout_data, "teams": teams, "terms": formatted_terms, "profile_user": user}
    )


@login_required
def account_view(request):
    user = request.user
    user_form = UserForm(instance=user)
    profile_form = UserProfileForm(instance=user.userprofile)
    saved = False

    if request.method == "POST":
        if "user" in request.POST:
            user_form = UserForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
        if "profile" in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user.userprofile)
            if profile_form.is_valid():
                profile_form.save()
        saved = True

    layout_data = get_layout_data(request)
    return render(
        request, "account.html", {**layout_data, "profile_form": profile_form, "user_form": user_form, "saved": saved}
    )


@user_passes_test(lambda u: u.is_superuser)
def server_settings_logo_form_view(request):
    if not request.method == "POST":
        return HttpResponse("Method not allowed", status=405)
    settings = ServerSettings.objects.get()
    form = ServerSettingsLogoForm(request.POST, request.FILES, instance=settings)
    if form.is_valid():
        form.instance.initial_setup_completed = True
        form.save()

    return redirect("club_settings")


@user_passes_test(lambda u: u.is_superuser)
def server_settings_view(request):
    layout_data = get_layout_data(request)
    if request.method == "POST":
        form = ServerSettingsForm(request.POST, instance=layout_data["settings"])
        if form.is_valid():
            form.instance.initial_setup_completed = True
            form.save()
    else:
        form = ServerSettingsForm(instance=layout_data["settings"])
    logo_form = ServerSettingsLogoForm(instance=layout_data["settings"])
    return render(request, "server_settings.html", {**layout_data, "form": form, "logo_form": logo_form})


class AttendanceListView(ListView):
    model = Attendance
    template_name = "profile_fragments/attendance_list.html"
    paginate_by = 5
    context_object_name = "attendances"

    def get_queryset(self):
        user_id = self.request.GET.get("user_id")
        if user_id and (
            self.request.user.is_staff or self.request.user.is_superuser or int(user_id) == self.request.user.id
        ):
            return Attendance.objects.order_by("-timestamp").filter(user_id=user_id)
        return Attendance.objects.order_by("-timestamp").filter(user=self.request.user)


@require_GET
def apple_merchant_id(request):
    if not settings.SQUARE_APPLE_MERCHANT_ID:
        return HttpResponse("Not configured", status=400)
    return HttpResponse(settings.SQUARE_APPLE_MERCHANT_ID, content_type="text/plain")


def index(request):
    return HttpResponseRedirect("/profile")
