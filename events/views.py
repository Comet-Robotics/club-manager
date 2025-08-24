from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404

from core.utilities import get_layout_data
from .forms import EventForm, SignInForm, CreateProfileForm, UserSearchForm, RSVPForm
from .models import UserIdentification, Attendance, Event, Reservation
from core.models import UserProfile
from django.contrib.auth.models import User
from django.contrib.admin.views.decorators import staff_member_required
from .tables import UserTable, LinkUserTable
from core.utilities import get_layout_data


@staff_member_required
def sign_in(request, event_id):
    layout_data = get_layout_data(request)
    current_event = Event.objects.get(pk=event_id)
    event_name = current_event.event_name
    if request.method == "POST":
        form = SignInForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data["card_data"]
            try:
                user_profile = UserIdentification.objects.get(student_id=student_id)
                if user_profile:
                    user = User.objects.get(username=user_profile.user)
                    valid_payment = UserProfile.objects.get(user=user).is_member()[1]
                    print(valid_payment)
                    form = SignInForm()
                    status, created = Attendance.objects.get_or_create(event=current_event, user=user_profile.user)
                    if created:
                        message = "success"
                        if not valid_payment:
                            message = "nomember"
                    else:
                        message = "repeat"
                        if not valid_payment:
                            message = "nomember"
            except UserIdentification.DoesNotExist:
                return redirect("lookup-user", event_id=event_id, student_id=student_id)

            return render(
                request,
                "sign_in.html",
                {
                    **layout_data,
                    "form": form,
                    "message": message,
                    "status": status,
                    "user": user_profile.user,
                    "event_id": event_id,
                    "event_name": event_name,
                },
            )

    else:
        form = SignInForm()

    return render(
        request, "sign_in.html", {**layout_data, "form": form, "event_id": event_id, "event_name": event_name}
    )


@staff_member_required
def pass_sign_in(request, event_id, user_id):
    current_event = Event.objects.get(pk=event_id)
    user = User.objects.get(pk=user_id)
    status, created = Attendance.objects.get_or_create(event=current_event, user=user)
    if created:
        print("success")
        message = "success"
    else:
        print("repeat")
        message = "repeat"
    return redirect("sign_in", event_id=event_id)


@staff_member_required
def pass_link(request, event_id, user_id, student_id):
    current_event = Event.objects.get(pk=event_id)
    user_profile = UserIdentification.link_user(user_id, student_id)
    user = User.objects.get(pk=user_id)
    status, created = Attendance.objects.get_or_create(event=current_event, user=user)
    print(user_profile)
    if created:
        print("success")
        message = "success"
    else:
        print("repeat")
        message = "repeat"
    return redirect("sign_in", event_id=event_id)


@staff_member_required
def create_profile(request, student_id):
    if request.method == "POST":
        form = CreateProfileForm(request.POST)
        if form.is_valid():
            net_id = form.cleaned_data["net_id"]
            first = form.cleaned_data["first_name"]
            last = form.cleaned_data["last_name"]
            UserIdentification.create_extended_user(net_id=net_id, student_id=student_id, first=first, last=last)
            return redirect("sign_in")
    else:
        form = CreateProfileForm()

    return render(request, "create_profile.html", {"form": form})


@staff_member_required
def lookup_user(request, event_id, student_id=None):
    if student_id:
        print("student id found")
        users = User.objects.filter(useridentification__isnull=True)
    else:
        users = User.objects.all()

    if request.method == "POST":
        form = UserSearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data["search"]
            users = (
                users.filter(first_name__icontains=query)
                | users.filter(last_name__icontains=query)
                | users.filter(useridentification__student_id__icontains=query)
                | users.filter(username__icontains=query)
            )
    else:
        form = UserSearchForm()

    if student_id:
        table = LinkUserTable(users, event_id=event_id, student_id=student_id)
    else:
        table = UserTable(users, event_id=event_id)
    return render(request, "lookup_user.html", {"users": users, "form": form, "table": table})


def rsvp(request, event_id):
    event = Event.objects.get(pk=event_id)
    if request.method == "POST":
        form = RSVPForm(request.POST)
        if form.is_valid():
            first = form.cleaned_data["first_name"]
            last = form.cleaned_data["last_name"]
            net_id = form.cleaned_data["net_id"]
            user = User.objects.filter(username=net_id).first()
            if not user:
                user = User.objects.create(username=net_id, first_name=first, last_name=last)
            if not Reservation.objects.filter(user=user, event=event).exists():
                reserved = Reservation.objects.create(event=event, user=user)
            return redirect(event.url)
            # return render(request, 'rsvp.html', {'form': form, 'user': user, 'event': event})
    else:
        form = RSVPForm()
    return render(request, "rsvp.html", {"event": event, "form": form})


def report(request, event_id):
    event = Event.objects.get(pk=event_id)
    attendance = Attendance.objects.filter(event=event)
    return render(request, "report.html", {"event": event, "attendances": attendance})


def event_overview(request, event_id):
    layout_data = get_layout_data(request)
    event = Event.objects.get(pk=event_id)
    return render(request, "event_overview.html", {**layout_data, "event": event})


def event_editor_view(request, event_id: int | None = None):
    layout_data = get_layout_data(request)
    if event_id:
        event = get_object_or_404(Event, pk=event_id)
        if request.method == "POST":
            form = EventForm(request.POST, instance=event)
            if form.is_valid():
                form.save()
                # Redirect back to project events page if event is associated with a project
                if event.project:
                    return redirect("events", project_id=event.project.id)
                else:
                    return redirect("event_overview", event_id=event.id)
        else:
            form = EventForm(instance=event)
        return render(request, "edit_event.html", {**layout_data, "form": form})
    else:
        form = EventForm()
        return render(request, "edit_event.html", {**layout_data, "form": form})


def create_event_view(request):
    layout_data = get_layout_data(request)
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save()
            # Check if project_id was provided and redirect to project events page
            project_id = form.cleaned_data.get('project_id')
            if project_id:
                return redirect("events", project_id=project_id)
            else:
                return redirect("event_editor_view", event_id=form.instance.id)
    else:
        # Get project_id from URL parameter and pre-populate the form
        project_id = request.GET.get('project_id')
        form = EventForm(initial={'project_id': project_id} if project_id else {})
    return render(request, "edit_event.html", {**layout_data, "form": form})
