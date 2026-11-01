"""Staff check-in workspace, gated by UNIFIED_EVENT_CHECK_IN."""

import re
import secrets
from collections.abc import Iterable, Mapping
from typing import Any, cast

from django import forms
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from accounts.forms import RegistrationCompletionForm
from common.forms import NetIDField
from core.models import UserProfile
from core.utilities import get_layout_data
from events.models import Attendance, Event, SignInMethod
from payments.models import Term


class NewAttendeeForm(RegistrationCompletionForm):
    net_id = NetIDField()
    field_order = ["net_id", "major", "first_name", "last_name"]

    def __init__(self, data: Mapping[str, Any] | None = None, **kwargs: Any) -> None:
        super().__init__(User(), data=data, **kwargs)
        self.initial = {name: value for name, value in self.initial.items() if value != ""}
        major = cast(forms.ChoiceField, self.fields["major"])
        major.required = False
        major.choices = [
            ("", "Select a major (optional)"),
            *cast(Iterable[tuple[Any, Any]], major.choices),
            ("unknown", "Unknown"),
        ]
        self.fields["first_name"].widget.attrs["autofocus"] = True

    def clean_net_id(self) -> str:
        net_id = cast(str, self.cleaned_data["net_id"])
        if User.objects.filter(username__iexact=net_id).exists():
            raise forms.ValidationError("This Net ID already exists. Search for the person instead.")
        return net_id


def _record_check_in(event: Event, user: User) -> dict[str, Any]:
    _, meta = user.userprofile.sign_in_to_event(event, SignInMethod.STAFF_INITIATED)
    active_terms = [term for term, _ in user.userprofile.get_active_membership_terms()]
    renewal_term = Term.get_active_term_with_latest_end_date()
    signed_in_at = timezone.now()
    return {
        "user_id": user.pk,
        "name": user.get_full_name() or user.username,
        "net_id": user.username,
        "already_signed_in": meta.already_signed_in,
        "unpaid": meta.is_not_member,
        "renewal": renewal_term.name if active_terms and renewal_term and renewal_term not in active_terms else "",
        "attendance_id": meta.attendance.pk if not meta.already_signed_in else None,
        "time": signed_in_at.isoformat(),
        "time_display": timezone.localtime(signed_in_at).strftime("%I:%M:%S %p").lstrip("0"),
    }


def _search_users(query: str) -> list[User]:
    return list(
        User.objects.select_related("userprofile")
        .annotate(full_name=Concat("first_name", Value(" "), "last_name"))
        .filter(Q(full_name__icontains=query) | Q(username__icontains=query))
        .order_by("first_name", "last_name", "username")[:25]
    )


def _attendee_initials_for_query(query: str) -> dict[str, str]:
    """Turn the text the operator already typed into add-person initial values."""
    value = query.strip()
    if not value:
        return {}
    if re.fullmatch(r"[A-Za-z]{3}\d{6}", value):
        return {"net_id": value.lower()}
    parts = value.split()
    if len(parts) > 1:
        return {"first_name": " ".join(parts[:-1]), "last_name": parts[-1]}
    return {"first_name": value}


def _focus_first_empty_field(new_form: NewAttendeeForm, initial: Mapping[str, str]) -> None:
    for field in new_form.fields.values():
        field.widget.attrs.pop("autofocus", None)
    focus_field = next((name for name in ("net_id", "first_name", "last_name") if not initial.get(name)), "major")
    new_form.fields[focus_field].widget.attrs["autofocus"] = True


def search_attendees(request: HttpRequest, event_id: int) -> HttpResponse:
    from django.conf import settings

    if not settings.FEATURE_FLAGS["UNIFIED_EVENT_CHECK_IN"]:
        raise Http404
    event = get_object_or_404(Event, pk=event_id)
    query = request.GET.get("entry", "").strip()[:100]
    pending = request.session.get(f"unified_check_in_{event_id}", {}).get("pending")
    if not query or ";" in query:
        return render(request, "partials/unified_check_in_search.html", {"event": event, "pending": pending})
    return render(
        request,
        "partials/unified_check_in_search.html",
        {"event": event, "query": query, "users": _search_users(query), "pending": pending},
    )


def search_net_ids(request: HttpRequest, event_id: int) -> HttpResponse:
    from django.conf import settings

    if not settings.FEATURE_FLAGS["UNIFIED_EVENT_CHECK_IN"]:
        raise Http404
    get_object_or_404(Event, pk=event_id)
    state = request.session.get(f"unified_check_in_{event_id}", {})
    pending = state.get("pending")
    if not pending:
        raise Http404
    field = request.GET.get("search_field", "net_id")
    if field not in {"net_id", "first_name", "last_name"}:
        raise Http404
    query = request.GET.get(field, "").strip()[:100]
    users = User.objects.none()
    if query and ";" not in query:
        users = (
            User.objects.select_related("userprofile")
            .annotate(full_name=Concat("first_name", Value(" "), "last_name"))
            .filter(Q(username__istartswith=query) | Q(full_name__icontains=query))
            .order_by("first_name", "last_name", "username")[:10]
        )
    template = "partials/net_id_suggestions.html"
    return render(request, template, {"users": users, "query": query, "search_field": field})


class SignInAction:
    """Apply one staff action to the event's existing sign-in session."""

    def __init__(self, request: HttpRequest, event: Event, state: dict[str, Any]) -> None:
        self.request = request
        self.event = event
        self.state = state
        self.error = ""
        self.query = ""
        self.new_form: NewAttendeeForm | None = None
        self.redirect = False

    def perform(self) -> str:
        action = self.request.POST.get("action", "submit")
        handlers = {
            "submit": self.submit,
            "correct": self.correct,
            "cancel": self.cancel,
            "search": self.search,
            "select": self.select,
            "new": self.add_person,
            "cancel_new": self.cancel_add_person,
            "create": self.create_person,
            "confirm": self.confirm_card_link,
        }
        handler = handlers.get(action)
        if handler:
            handler()
        return action

    def record_sign_in(self, user: User, card: str | None = None) -> None:
        result = _record_check_in(self.event, user)
        if card is not None:
            result["card"] = card
        self.state["result"] = result

    def prepare_card_confirmation(self, user_id: int, target_card: str | None) -> None:
        pending = self.state["pending"]
        pending["target_id"] = user_id
        pending["target_card"] = target_card
        pending["confirmation"] = secrets.token_urlsafe(24)

    def submit(self) -> None:
        entry = self.request.POST.get("entry", "").strip()
        if ";" in entry:
            self.swipe_card(entry[entry.index(";") :])
        elif entry:
            self.search_for(entry)
        else:
            self.error = "Swipe a card or enter a name or Net ID."

    def swipe_card(self, entry: str) -> None:
        match = re.fullmatch(r";(\d{16})=[^\s]*", entry)
        if not match:
            self.error = "Card data was incomplete or invalid. Try the swipe again."
            return

        card = match.group(1)
        self.state.pop("pending", None)
        profile = UserProfile.objects.select_related("user").filter(comet_card_serial_number=card).first()
        if profile:
            self.record_sign_in(profile.user, card)
            self.redirect = True
        else:
            self.state["pending"] = {"card": card, "owner_id": None, "attendance_id": None}
            self.state.pop("result", None)
            self.redirect = True

    def correct(self) -> None:
        result = self.state.get("result", {})
        if not result.get("card"):
            self.error = "There is no card swipe to correct."
            return
        self.state["pending"] = {
            "card": result["card"],
            "owner_id": result["user_id"],
            "attendance_id": result.get("attendance_id"),
        }

    def cancel(self) -> None:
        self.state.pop("pending", None)

    def search(self) -> None:
        self.search_for(self.request.POST.get("entry", "").strip())

    def search_for(self, query: str) -> None:
        self.query = query[:100]
        if self.state.get("pending"):
            self.state["pending"].pop("target_id", None)

    def select(self) -> None:
        user = get_object_or_404(User.objects.select_related("userprofile"), pk=self.request.POST.get("user_id"))
        pending = self.state.get("pending")
        from_netid_form = self.request.POST.get("from_netid_form") == "1"

        if not pending:
            if from_netid_form:
                self.error = "The scanned card is no longer available. Please swipe it again."
            else:
                self.record_sign_in(user)
                self.redirect = True
            return

        if from_netid_form and self.request.POST.get("net_id", "").strip().lower() != user.username.lower():
            self.error = "The selected person changed. Please search for them again."
        elif from_netid_form and pending.get("owner_id") is None:
            self.link_unowned_card(user, pending)
        else:
            self.prepare_card_confirmation(user.pk, user.userprofile.comet_card_serial_number)

    def link_unowned_card(self, user: User, pending: dict[str, Any]) -> None:
        try:
            with transaction.atomic():
                profile = UserProfile.objects.select_for_update().get(pk=user.pk)
                if UserProfile.objects.filter(comet_card_serial_number=pending["card"]).exists():
                    raise ValueError("The card association changed. Please swipe it again.")
                if profile.comet_card_serial_number:
                    self.prepare_card_confirmation(user.pk, profile.comet_card_serial_number)
                else:
                    profile.comet_card_serial_number = pending["card"]
                    profile.save(update_fields=["comet_card_serial_number"])
                    self.record_sign_in(user, pending["card"])
                    self.state.pop("pending")
                    self.redirect = True
        except (IntegrityError, ValueError) as exc:
            self.error = str(exc) if isinstance(exc, ValueError) else "The card changed. Please swipe it again."
            self.state.pop("pending", None)

    def add_person(self) -> None:
        if self.state.get("pending"):
            self.state["pending"].pop("target_id", None)
        else:
            self.state["search_context"] = self.request.POST.get("search_query", "").strip()[:100]
        self.new_form = NewAttendeeForm()

    def cancel_add_person(self) -> None:
        self.state.pop("search_context", None)

    def create_person(self) -> None:
        form = NewAttendeeForm(self.request.POST)
        self.new_form = form
        if not form.is_valid():
            return

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["net_id"],
                    first_name=form.cleaned_data["first_name"],
                    last_name=form.cleaned_data["last_name"],
                )
                user.userprofile.major = form.cleaned_data["major"] or None
                user.userprofile.save()
                pending = self.state.get("pending")
                if not pending:
                    self.record_sign_in(user)
                    self.redirect = True
                elif pending["owner_id"] is None:
                    user.userprofile.comet_card_serial_number = pending["card"]
                    user.userprofile.save(update_fields=["comet_card_serial_number"])
                    self.record_sign_in(user, pending["card"])
                    self.state.pop("pending")
                    self.redirect = True
                else:
                    self.prepare_card_confirmation(user.pk, None)
        except IntegrityError:
            if User.objects.filter(username__iexact=form.cleaned_data["net_id"]).exists():
                form.add_error("net_id", "This Net ID already exists. Search for the person instead.")
            else:
                form.add_error(None, "The card changed while saving. Please swipe it again.")
        else:
            self.new_form = None

    def confirm_card_link(self) -> None:
        pending = self.state.get("pending")
        confirmation = self.request.POST.get("confirmation", "")
        if (
            not pending
            or not pending.get("target_id")
            or not secrets.compare_digest(pending.get("confirmation", ""), confirmation)
            or not pending.get("confirmation")
        ):
            self.error = "This card action has expired. Please swipe the card again."
            return

        try:
            with transaction.atomic():
                target = get_object_or_404(UserProfile.objects.select_for_update(), pk=pending["target_id"])
                owner = UserProfile.objects.select_for_update().filter(comet_card_serial_number=pending["card"]).first()
                if (owner.pk if owner else None) != pending["owner_id"]:
                    raise ValueError("The card association changed. Swipe again to review it.")
                if target.comet_card_serial_number != pending.get("target_card"):
                    raise ValueError("This person’s card changed. Swipe again to review it.")
                if owner and owner.pk != target.pk:
                    owner.comet_card_serial_number = None
                    owner.save(update_fields=["comet_card_serial_number"])
                    # Only undo attendance created by the swipe being corrected.
                    if pending.get("attendance_id"):
                        Attendance.objects.filter(
                            pk=pending["attendance_id"], event=self.event, user_id=owner.pk
                        ).delete()
                target.comet_card_serial_number = pending["card"]
                target.save(update_fields=["comet_card_serial_number"])
                self.record_sign_in(target.user, pending["card"])
            self.state.pop("pending", None)
            self.redirect = True
        except (IntegrityError, ValueError) as exc:
            self.error = str(exc) if isinstance(exc, ValueError) else "The card changed. Please swipe it again."
            self.state.pop("pending", None)


def unified_check_in(request: HttpRequest, event_id: int) -> HttpResponse:
    event = get_object_or_404(Event, pk=event_id)
    key = f"unified_check_in_{event_id}"
    state = request.session.get(key, {})
    is_htmx = request.headers.get("HX-Request") == "true"
    if request.method == "GET" and not is_htmx:
        resume = state.pop("resume", None)
        supplied_resume = request.GET.get("resume", "")
        if not resume or not supplied_resume.isascii() or not secrets.compare_digest(resume, supplied_resume):
            state = {}
    error = ""
    query = ""
    users = []
    new_form: NewAttendeeForm | None = None
    redirect_to_check_in = False

    if request.method == "POST":
        sign_in = SignInAction(request, event, state)
        action = sign_in.perform()
        error = sign_in.error
        query = sign_in.query
        new_form = sign_in.new_form
        redirect_to_check_in = sign_in.redirect

    if error or (new_form is not None and new_form.is_bound and new_form.errors):
        state.pop("result", None)

    if query:
        users = _search_users(query)
        if request.method == "POST" and action == "submit" and not users:
            new_form = NewAttendeeForm()
            if not state.get("pending"):
                state["search_context"] = query

    pending = state.get("pending")
    target = User.objects.select_related("userprofile").filter(pk=pending.get("target_id")).first() if pending else None
    owner = User.objects.filter(pk=pending.get("owner_id")).first() if pending and pending.get("owner_id") else None
    use_netid_form = bool(pending and not target)
    if use_netid_form:
        if new_form is None:
            new_form = NewAttendeeForm()
        new_form.fields["first_name"].widget.attrs.pop("autofocus", None)
        new_form.fields["net_id"].widget.attrs["autofocus"] = True
        for name in ("net_id", "first_name", "last_name"):
            new_form.fields[name].widget.attrs.update(
                {
                    "hx-get": reverse("unified_check_in_net_ids", args=[event_id]),
                    "hx-trigger": "input changed delay:150ms",
                    "hx-target": f"#{name}-suggestions",
                    "hx-vals": f'{{"search_field":"{name}"}}',
                    "hx-swap": "innerHTML",
                    "hx-sync": "this:replace",
                    "aria-autocomplete": "list",
                    "role": "combobox",
                }
            )
    if new_form is not None and not new_form.is_bound:
        prefill = query or state.get("search_context", "")
        initial = _attendee_initials_for_query(prefill)
        if initial:
            new_form.initial = {**new_form.initial, **initial}
            _focus_first_empty_field(new_form, initial)
    if redirect_to_check_in and not is_htmx:
        state["resume"] = secrets.token_urlsafe(24)
        request.session[key] = state
        return redirect(f"{reverse('unified_check_in', args=[event_id])}?resume={state['resume']}")
    request.session[key] = state
    return render(
        request,
        "partials/checkin_response.html" if is_htmx and request.method == "POST" else "unified_check_in.html",
        {
            **get_layout_data(request),
            "event": event,
            "state": state,
            "pending": pending,
            "target": target,
            "owner": owner,
            "users": users,
            "query": query,
            "error": error,
            "new_form": new_form,
            "use_netid_form": use_netid_form,
        },
    )
