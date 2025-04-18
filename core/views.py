from django.shortcuts import redirect, render
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.views.decorators.http import require_GET
from django.conf import settings
from core.models import ServerSettings
from core.utilities import get_layout_data
from events.models import Attendance
from django.views.generic import ListView
from .forms import ServerSettingsLogoForm, UserProfileForm, UserForm, ServerSettingsForm
from projects.models import Team
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test


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
def profile_view(request):
    layout_data = get_layout_data(request)
    teams = Team.get_teams_associated_with_user(request.user)
    terms = [term for term, purchased_product in request.user.userprofile.get_membership_terms()]
    formatted_terms = [initials(term.name) for term in terms]

    return render(request, "profile.html", {**layout_data, "teams": teams, "terms": formatted_terms})


@login_required
def account_view(request):
    # NOTE: temporarily restricting page access in production until the corresponding page is implemented
    if not settings.DEBUG:
        return HttpResponse("This page is under construction - only available in DEBUG mode.")

    user = request.user
    user_form = UserForm(instance=user)
    profile_form = UserProfileForm(instance=user.userprofile)

    if request.method == "POST":
        if "user" in request.POST:
            user_form = UserForm(request.POST, instance=user)
            if user_form.is_valid():
                user_form.save()
        if "profile" in request.POST:
            profile_form = UserProfileForm(request.POST, instance=user.userprofile)
            if profile_form.is_valid():
                profile_form.save()

    layout_data = get_layout_data(request)
    return render(request, "account.html", {**layout_data, "profile_form": profile_form, "user_form": user_form})


@user_passes_test(lambda u: u.is_superuser)
def server_settings_logo_form_view(request):
    if not request.method == "POST":
        return HttpResponse("Method not allowed", status=405)
    settings = ServerSettings.objects.get()
    form = ServerSettingsLogoForm(request.POST, request.FILES, instance=settings)
    if form.is_valid():
        form.save()

    return redirect("server_settings")


@user_passes_test(lambda u: u.is_superuser)
def server_settings_view(request):
    layout_data = get_layout_data(request)
    if request.method == "POST":
        form = ServerSettingsForm(request.POST, instance=layout_data["settings"])
        if form.is_valid():
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
        return Attendance.objects.order_by("-timestamp").filter(user=self.request.user)


def spa_view(request):
    return render(request, "spa.html", {"DEBUG": settings.DEBUG})


@require_GET
def apple_merchant_id(request):
    if not settings.SQUARE_APPLE_MERCHANT_ID:
        return HttpResponse("Not configured", status=400)
    return HttpResponse(settings.SQUARE_APPLE_MERCHANT_ID, content_type="text/plain")


def index(request):
    return HttpResponsePermanentRedirect("/profile")
