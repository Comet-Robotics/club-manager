"""Staff check-in workspace, gated by UNIFIED_EVENT_CHECK_IN."""

import re
import secrets
from collections.abc import Sequence
from typing import cast

from django import forms
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q, Value
from django.db.models.functions import Concat
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from common.forms import NetIDField
from core.models import UserProfile
from core.utilities import get_layout_data
from events.models import Attendance, Event, SignInMethod
from payments.models import Term


class NewAttendeeForm(forms.Form):
    net_id = NetIDField()
    major = forms.ChoiceField(
        choices=[("", "Select a major (optional)")]
        + list(cast(Sequence[tuple[str, str]], UserProfile._meta.get_field("major").choices)),
        required=False,
    )
    first_name = forms.CharField(max_length=100, label="First name", widget=forms.TextInput(attrs={"autofocus": True}))
    last_name = forms.CharField(max_length=100, label="Last name")

    def clean_net_id(self):
        net_id = self.cleaned_data["net_id"]
        if User.objects.filter(username__iexact=net_id).exists():
            raise forms.ValidationError("This Net ID already exists. Search for the person instead.")
        return net_id


def _record_check_in(event, user):
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


def _search_users(query):
    return list(
        User.objects.select_related("userprofile")
        .annotate(full_name=Concat("first_name", Value(" "), "last_name"))
        .filter(Q(full_name__icontains=query) | Q(username__icontains=query))
        .order_by("first_name", "last_name", "username")[:25]
    )


def _attendee_initials_for_query(query):
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


def _focus_first_empty_field(new_form, initial):
    for name, field in new_form.fields.items():
        field.widget.attrs.pop("autofocus", None)
    focus_field = next((name for name in ("net_id", "first_name", "last_name") if not initial.get(name)), "major")
    new_form.fields[focus_field].widget.attrs["autofocus"] = True


def search_attendees(request, event_id):
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


def search_net_ids(request, event_id):
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


def unified_check_in(request, event_id):
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
    new_form = None
    redirect_to_check_in = False

    if request.method == "POST":
        action = request.POST.get("action", "submit")
        if action == "submit":
            value = request.POST.get("entry", "").strip()
            if ";" in value:
                value = value[value.index(";") :]
                match = re.fullmatch(r";(\d{16})=[^\s]*", value)
                if not match:
                    error = "Card data was incomplete or invalid. Try the swipe again."
                else:
                    card = match.group(1)
                    state.pop("pending", None)
                    profile = UserProfile.objects.select_related("user").filter(comet_card_serial_number=card).first()
                    if profile:
                        result = _record_check_in(event, profile.user)
                        result["card"] = card
                        state["result"] = result
                        redirect_to_check_in = True
                    else:
                        state["pending"] = {"card": card, "owner_id": None, "attendance_id": None}
                        state.pop("result", None)
                        redirect_to_check_in = True
            elif value:
                query = value[:100]
                if state.get("pending"):
                    state["pending"].pop("target_id", None)
            else:
                error = "Swipe a card or enter a name or Net ID."
        elif action == "correct":
            result = state.get("result", {})
            if result.get("card"):
                state["pending"] = {
                    "card": result["card"],
                    "owner_id": result["user_id"],
                    "attendance_id": result.get("attendance_id"),
                }
            else:
                error = "There is no card swipe to correct."
        elif action == "cancel":
            state.pop("pending", None)
        elif action == "search":
            query = request.POST.get("entry", "").strip()[:100]
            if state.get("pending"):
                state["pending"].pop("target_id", None)
        elif action == "select":
            user = get_object_or_404(User.objects.select_related("userprofile"), pk=request.POST.get("user_id"))
            if state.get("pending"):
                pending = state["pending"]
                from_netid_form = request.POST.get("from_netid_form") == "1"
                if from_netid_form and request.POST.get("net_id", "").strip().lower() != user.username.lower():
                    error = "The selected person changed. Please search for them again."
                elif from_netid_form and pending.get("owner_id") is None:
                    try:
                        with transaction.atomic():
                            profile = UserProfile.objects.select_for_update().get(pk=user.pk)
                            if UserProfile.objects.filter(comet_card_serial_number=pending["card"]).exists():
                                raise ValueError("The card association changed. Please swipe it again.")
                            if profile.comet_card_serial_number:
                                pending["target_id"] = user.pk
                                pending["target_card"] = profile.comet_card_serial_number
                                pending["confirmation"] = secrets.token_urlsafe(24)
                            else:
                                profile.comet_card_serial_number = pending["card"]
                                profile.save(update_fields=["comet_card_serial_number"])
                                result = _record_check_in(event, user)
                                result["card"] = pending["card"]
                                state["result"] = result
                                state.pop("pending")
                                redirect_to_check_in = True
                    except (IntegrityError, ValueError) as exc:
                        error = str(exc) if isinstance(exc, ValueError) else "The card changed. Please swipe it again."
                        state.pop("pending", None)
                else:
                    pending["target_id"] = user.pk
                    pending["target_card"] = user.userprofile.comet_card_serial_number
                    pending["confirmation"] = secrets.token_urlsafe(24)
            else:
                if request.POST.get("from_netid_form") == "1":
                    error = "The scanned card is no longer available. Please swipe it again."
                else:
                    state["result"] = _record_check_in(event, user)
                    redirect_to_check_in = True
        elif action == "new":
            if state.get("pending"):
                state["pending"].pop("target_id", None)
            else:
                state["search_context"] = request.POST.get("search_query", "").strip()[:100]
            new_form = NewAttendeeForm()
        elif action == "cancel_new":
            state.pop("search_context", None)  # Keep any scanned card so the operator can continue the lookup.
        elif action == "create":
            new_form = NewAttendeeForm(request.POST)
            if new_form.is_valid():
                try:
                    with transaction.atomic():
                        user = User.objects.create_user(
                            username=new_form.cleaned_data["net_id"],
                            first_name=new_form.cleaned_data["first_name"],
                            last_name=new_form.cleaned_data["last_name"],
                        )
                        user.userprofile.major = new_form.cleaned_data["major"] or None
                        user.userprofile.save()
                        if state.get("pending"):
                            pending = state["pending"]
                            if pending["owner_id"] is None:
                                user.userprofile.comet_card_serial_number = pending["card"]
                                user.userprofile.save(update_fields=["comet_card_serial_number"])
                                result = _record_check_in(event, user)
                                result["card"] = pending["card"]
                                state["result"] = result
                                state.pop("pending")
                                redirect_to_check_in = True
                            else:
                                pending["target_id"] = user.pk
                                pending["target_card"] = None
                                pending["confirmation"] = secrets.token_urlsafe(24)
                        else:
                            state["result"] = _record_check_in(event, user)
                            redirect_to_check_in = True
                except IntegrityError:
                    if User.objects.filter(username__iexact=new_form.cleaned_data["net_id"]).exists():
                        new_form.add_error("net_id", "This Net ID already exists. Search for the person instead.")
                    else:
                        new_form.add_error(None, "The card changed while saving. Please swipe it again.")
                else:
                    new_form = None
        elif action == "confirm":
            pending = state.get("pending")
            if (
                not pending
                or not pending.get("target_id")
                or not secrets.compare_digest(pending.get("confirmation", ""), request.POST.get("confirmation", ""))
                or not pending.get("confirmation")
            ):
                error = "This card action has expired. Please swipe the card again."
            else:
                try:
                    with transaction.atomic():
                        target_profile = get_object_or_404(
                            UserProfile.objects.select_for_update(), pk=pending["target_id"]
                        )
                        owner_profile = (
                            UserProfile.objects.select_for_update()
                            .filter(comet_card_serial_number=pending["card"])
                            .first()
                        )
                        if (owner_profile.pk if owner_profile else None) != pending["owner_id"]:
                            raise ValueError("The card association changed. Swipe again to review it.")
                        if target_profile.comet_card_serial_number != pending.get("target_card"):
                            raise ValueError("This person’s card changed. Swipe again to review it.")
                        if owner_profile and owner_profile.pk != target_profile.pk:
                            owner_profile.comet_card_serial_number = None
                            owner_profile.save(update_fields=["comet_card_serial_number"])
                            if pending.get("attendance_id"):
                                Attendance.objects.filter(
                                    pk=pending["attendance_id"], event=event, user_id=owner_profile.pk
                                ).delete()
                        target_profile.comet_card_serial_number = pending["card"]
                        target_profile.save(update_fields=["comet_card_serial_number"])
                        result = _record_check_in(event, target_profile.user)
                        result["card"] = pending["card"]
                        state["result"] = result
                    state.pop("pending", None)
                    redirect_to_check_in = True
                except (IntegrityError, ValueError) as exc:
                    error = str(exc) if isinstance(exc, ValueError) else "The card changed. Please swipe it again."
                    state.pop("pending", None)

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
