from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.forms import RegistrationCompletionForm
from events.models import Attendance, Event
from events.unified_check_in import NewAttendeeForm


@override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "UNIFIED_EVENT_CHECK_IN": True})
class UnifiedCheckInTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user("staff", password="pass", is_staff=True)
        self.client.force_login(self.staff)
        self.event = Event.objects.create(event_name="Meeting", event_date=timezone.now())
        self.url = reverse("unified_check_in", args=[self.event.pk])
        self.default_url = reverse("sign_in", args=[self.event.pk])
        self.original_url = reverse("original_sign_in", args=[self.event.pk])
        self.search_url = reverse("unified_check_in_search", args=[self.event.pk])
        self.netids_url = reverse("unified_check_in_net_ids", args=[self.event.pk])
        self.alex = User.objects.create_user("axr240001", first_name="Alex", last_name="Rivera")
        self.jordan = User.objects.create_user("jxl240002", first_name="Jordan", last_name="Lee")
        self.alex.userprofile.comet_card_serial_number = "1234567890123456"
        self.alex.userprofile.save()

    def post(self, **data):
        return self.client.post(self.url, data)

    def swipe(self, card="1234567890123456"):
        return self.post(action="submit", entry=f";{card}=0000000000000000?")

    def confirm(self):
        session = self.client.session[f"unified_check_in_{self.event.pk}"]
        return self.post(action="confirm", confirmation=session["pending"]["confirmation"])

    def follow_checkin_redirect(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(f"{self.url}?resume="))
        return self.client.get(response.url)

    def test_both_interfaces_are_available_and_link_to_each_other(self):
        self.assertTemplateUsed(self.client.get(self.default_url), "unified_check_in.html")
        original = self.client.get(self.original_url)
        self.assertTemplateUsed(original, "sign_in.html")
        self.assertContains(original, self.url)
        new = self.client.get(self.url)
        self.assertTemplateUsed(new, "unified_check_in.html")
        self.assertContains(new, self.original_url)

    def test_flag_off_preserves_legacy_page(self):
        with override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "UNIFIED_EVENT_CHECK_IN": False}):
            response = self.client.get(self.default_url)
            self.assertEqual(self.client.get(self.url).status_code, 404)
            self.assertNotContains(response, self.url)
        self.assertTemplateUsed(response, "sign_in.html")

    def test_original_lookup_returns_to_original_sign_in(self):
        response = self.client.get(reverse("pass_sign_in", args=[self.event.pk, self.alex.pk]))
        self.assertRedirects(response, self.original_url)

    def test_default_route_accepts_swipes_when_enabled(self):
        response = self.client.post(
            self.default_url,
            {"action": "submit", "entry": ";1234567890123456=0000000000000000?"},
            HTTP_HX_REQUEST="true",
            follow=True,
        )
        self.assertContains(response, "Alex Rivera")
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.alex).exists())

    def test_swipe_records_attendance_and_shows_result_after_redirect(self):
        response = self.swipe()
        result = self.follow_checkin_redirect(response)
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.alex).exists())
        self.assertContains(result, "Alex Rivera")
        self.assertContains(result, 'class="alert alert-success checkin-result"')

    def test_fresh_navigation_clears_display_but_not_attendance(self):
        response = self.follow_checkin_redirect(self.swipe())
        self.assertContains(response, "Alex Rivera")
        self.assertNotContains(self.client.get(self.url), "Alex Rivera")
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.alex).exists())

    def test_refresh_after_redirect_does_not_restore_previous_result(self):
        response = self.swipe()
        self.assertContains(self.follow_checkin_redirect(response), "Alex Rivera")
        self.assertNotContains(self.client.get(response.url), "Alex Rivera")

    def test_fresh_navigation_clears_unfinished_card_link(self):
        self.assertContains(self.follow_checkin_redirect(self.swipe("9999999999999999")), "isn’t linked yet")
        self.assertNotContains(self.client.get(self.url), "isn’t linked yet")
        self.assertNotContains(self.client.get(self.search_url, {"entry": "Alex"}), "Card linked")

    def test_swipe_after_search_text_still_checks_in(self):
        response = self.post(action="submit", entry="Alex;1234567890123456=0000000000000000?")
        self.follow_checkin_redirect(response)
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.alex).exists())

    def test_incomplete_swipe_after_text_is_not_treated_as_search(self):
        response = self.post(action="submit", entry="Alex;123=")
        self.assertContains(response, "Card data was incomplete or invalid")
        self.assertContains(response, 'class="alert alert-error checkin-alert"')
        self.assertNotContains(response, "No matches")

    def test_unknown_swipe_redirects_so_refresh_does_not_repeat_the_action(self):
        response = self.swipe("9999999999999999")
        result = self.follow_checkin_redirect(response)
        self.assertContains(result, "This card isn’t linked yet")
        self.assertContains(result, 'value="9999999999999999" disabled')
        self.assertContains(result, 'placeholder="Search by name or Net ID..."')

    def test_htmx_swipe_returns_update_regions_without_redirect(self):
        response = self.client.post(
            self.url,
            {"action": "submit", "entry": ";1234567890123456=0000000000000000?"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<main class="checkin">')
        self.assertEqual(response.content.count(b'hx-swap-oob="true"'), 2)
        self.assertContains(response, 'id="checkin-status"')
        self.assertContains(response, 'id="checkin-details"')
        self.assertContains(response, 'id="checkin-context"')
        self.assertContains(response, "Alex Rivera")
        self.assertEqual(Attendance.objects.filter(event=self.event, user=self.alex).count(), 1)
        self.assertContains(self.client.get(self.url, HTTP_HX_REQUEST="true"), "Alex Rivera")
        self.assertNotContains(self.client.get(self.url), "Alex Rivera")

    def test_htmx_unknown_swipe_keeps_pending_card_until_navigation(self):
        response = self.client.post(
            self.url,
            {"action": "submit", "entry": ";9999999999999999=0000000000000000?"},
            HTTP_HX_REQUEST="true",
            follow=True,
        )
        self.assertContains(response, "This card isn’t linked yet")
        self.assertContains(self.client.get(self.search_url, {"entry": "Alex"}), "Card linked")
        self.assertNotContains(self.client.get(self.url), "isn’t linked yet")

    def test_net_id_suggestions_match_net_ids_and_names_without_checking_in(self):
        self.swipe("9999999999999999")
        response = self.client.get(self.netids_url, {"net_id": "axr24"})
        self.assertContains(response, "axr240001")
        self.assertContains(response, "Card linked")
        by_name = self.client.get(self.netids_url, {"net_id": "Alex Rivera"})
        self.assertContains(by_name, "axr240001")
        self.assertFalse(Attendance.objects.filter(event=self.event, user=self.alex).exists())

    def test_creation_name_fields_search_without_net_id_length_limit(self):
        self.swipe("9999999999999999")
        self.jordan.first_name = "Alexandria"
        self.jordan.last_name = "Montgomery"
        self.jordan.save(update_fields=["first_name", "last_name"])
        for field, value in (("first_name", "Alexandria"), ("last_name", "Montgomery")):
            response = self.client.get(self.netids_url, {"search_field": field, field: value})
            self.assertContains(response, "jxl240002")
            self.assertContains(response, f'id="{field}-listbox"')
        page = self.client.get(self.url, HTTP_HX_REQUEST="true")
        self.assertContains(page, 'id="first_name-suggestions"')
        self.assertContains(page, 'id="last_name-suggestions"')
        self.assertContains(page, 'maxlength="9"')
        self.assertFalse(Attendance.objects.filter(event=self.event, user=self.jordan).exists())

    def test_creation_search_rejects_unknown_search_field(self):
        self.swipe("9999999999999999")
        self.assertEqual(self.client.get(self.netids_url, {"search_field": "email", "email": "test"}).status_code, 404)

    def test_net_id_suggestions_are_empty_without_swiped_card(self):
        self.assertEqual(self.client.get(self.netids_url, {"net_id": "axr24"}).status_code, 404)

    def test_combobox_markup_follows_the_headless_input_pattern(self):
        response = self.follow_checkin_redirect(self.swipe("9999999999999999"))
        self.assertContains(response, 'role="combobox"')
        self.assertContains(response, 'aria-autocomplete="list"')
        self.assertContains(response, 'aria-expanded="false"')
        self.assertNotContains(response, "Try native dropdown")
        self.assertNotContains(response, 'list="')
        search = self.client.get(f"{self.search_url}?entry=Jordan")
        self.assertContains(search, 'role="listbox" id="search-listbox"')
        self.assertContains(search, 'role="option" tabindex="-1" id="person-option-')

    def test_net_id_options_carry_listbox_semantics(self):
        self.swipe("9999999999999999")
        options = self.client.get(f"{self.netids_url}?net_id=axr24")
        self.assertContains(options, 'role="listbox" id="net-id-listbox"')
        self.assertContains(options, 'role="option" tabindex="-1" id="netid-option-')
        self.assertContains(options, 'data-net-id="axr240001"')

    def test_live_search_is_a_fragment_and_does_not_check_anyone_in(self):
        response = self.client.get(self.search_url, {"entry": "Alex Rivera"})
        self.assertContains(response, "Alex Rivera")
        self.assertContains(response, "Sign in")
        self.assertContains(response, "data-signin-action")
        self.assertNotContains(response, "<!DOCTYPE html>")
        self.assertFalse(Attendance.objects.filter(event=self.event).exists())

    def test_submitting_an_unmatched_search_opens_add_person(self):
        response = self.post(action="submit", entry="notfound")
        self.assertContains(response, "Add a person")
        self.assertEqual(response.context["new_form"].initial, {"first_name": "notfound"})
        self.assertTrue(response.context["new_form"].fields["net_id"].widget.attrs["autofocus"])
        self.assertContains(response, 'name="action" value="cancel_new"')
        self.assertContains(response, 'value="notfound" disabled')
        self.assertNotContains(response, "First name, last name, and Net ID are required.")
        self.assertFalse(User.objects.filter(username="notfound").exists())

    def test_submitting_a_matching_search_still_shows_the_matches(self):
        response = self.post(action="submit", entry="Alex")
        self.assertContains(response, "Alex Rivera")
        self.assertNotContains(response, 'name="action" value="cancel_new"')

    def test_htmx_unmatched_search_keeps_pending_card_and_merged_form(self):
        self.swipe("9999999999999999")
        response = self.client.post(self.url, {"entry": "notfound"}, HTTP_HX_REQUEST="true")
        self.assertContains(response, "This card isn’t linked yet")
        self.assertContains(response, "data-netid-form")
        self.assertContains(response, 'value="9999999999999999" disabled')
        self.assertNotContains(response, 'name="action" value="cancel_new"')
        self.assertEqual(
            self.client.session[f"unified_check_in_{self.event.pk}"]["pending"]["card"], "9999999999999999"
        )

    def test_cancel_discards_pending_card_and_returns_to_swipe(self):
        self.swipe("9999999999999999")
        response = self.post(action="cancel")
        self.assertNotContains(response, "This card isn’t linked yet")
        self.assertNotContains(response, 'class="checkin-new" data-netid-form')
        self.assertNotIn(
            "pending",
            self.client.session[f"unified_check_in_{self.event.pk}"],
        )

    def test_net_id_form_links_card_and_signs_in_existing_person_without_card(self):
        self.swipe("9999999999999999")
        response = self.post(action="select", user_id=self.jordan.pk, from_netid_form="1", net_id="jxl240002")
        result = self.follow_checkin_redirect(response)
        self.assertContains(result, "Jordan Lee")
        self.jordan.userprofile.refresh_from_db()
        self.assertEqual(self.jordan.userprofile.comet_card_serial_number, "9999999999999999")
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.jordan).exists())

    def test_net_id_form_confirms_before_replacing_an_existing_card(self):
        self.swipe("9999999999999999")
        response = self.post(action="select", user_id=self.alex.pk, from_netid_form="1", net_id="axr240001")
        self.assertContains(response, "previously linked card")
        self.alex.userprofile.refresh_from_db()
        self.assertEqual(self.alex.userprofile.comet_card_serial_number, "1234567890123456")
        self.follow_checkin_redirect(self.confirm())
        self.alex.userprofile.refresh_from_db()
        self.assertEqual(self.alex.userprofile.comet_card_serial_number, "9999999999999999")

    def test_net_id_form_rejects_a_mismatched_selection(self):
        self.swipe("9999999999999999")
        response = self.post(action="select", user_id=self.jordan.pk, from_netid_form="1", net_id="axr240001")
        self.assertContains(response, "The selected person changed")
        self.jordan.userprofile.refresh_from_db()
        self.assertIsNone(self.jordan.userprofile.comet_card_serial_number)
        self.assertFalse(Attendance.objects.filter(event=self.event).exists())

    def test_add_person_from_search_keeps_query_as_disabled_context(self):
        response = self.post(action="new", search_query="Alex Rivera")
        self.assertContains(response, 'value="Alex Rivera" disabled')
        self.assertContains(response, 'name="first_name"')
        cancelled = self.post(action="cancel_new")
        self.assertNotContains(cancelled, 'id="context-entry"')

    def test_unmatched_search_prefills_the_add_person_form(self):
        net_id_like = self.post(action="submit", entry="xyz240001")
        self.assertEqual(net_id_like.context["new_form"].initial, {"net_id": "xyz240001"})
        self.assertTrue(net_id_like.context["new_form"].fields["first_name"].widget.attrs["autofocus"])
        self.assertContains(net_id_like, 'value="xyz240001"')

        two_names = self.post(action="submit", entry="Ada Lovelace")
        self.assertEqual(two_names.context["new_form"].initial, {"first_name": "Ada", "last_name": "Lovelace"})
        self.assertTrue(two_names.context["new_form"].fields["net_id"].widget.attrs["autofocus"])

        three_names = self.post(action="submit", entry="Mary Jane Watson")
        self.assertEqual(three_names.context["new_form"].initial, {"first_name": "Mary Jane", "last_name": "Watson"})

        one_name = self.post(action="submit", entry="Cher")
        self.assertEqual(one_name.context["new_form"].initial, {"first_name": "Cher"})
        self.assertTrue(one_name.context["new_form"].fields["net_id"].widget.attrs["autofocus"])

    def test_result_includes_clock_time_with_seconds(self):
        response = self.follow_checkin_redirect(self.swipe())
        self.assertContains(response, 'class="result-age result-time"')
        self.assertRegex(response.context["state"]["result"]["time_display"], r"^\d{1,2}:\d{2}:\d{2} [AP]M$")

    def test_search_does_not_inherit_swipe_response_selectors(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'hx-disinherit="hx-sync"')
        self.assertContains(response, 'hx-trigger="input changed delay:150ms"')
        self.assertContains(response, 'id="search-progress"')
        self.assertContains(response, 'id="signin-loading"')
        self.assertContains(response, "Signing in…")
        self.assertContains(response, 'aria-live="polite" aria-label="Searching" aria-hidden="true"')

    def test_live_search_with_pending_card_offers_linking(self):
        self.swipe("9999999999999999")
        response = self.client.get(self.search_url, {"entry": "Alex"})
        self.assertContains(response, "Select")
        self.assertContains(response, "Card linked")
        self.assertNotContains(response, "data-signin-action")
        self.assertNotContains(response, "Add a new person")

    def test_search_results_share_one_form_and_preserve_both_actions(self):
        response = self.client.get(self.search_url, {"entry": "Alex"})
        self.assertContains(response, '<form method="post" data-search-results-form', count=1)
        self.assertContains(response, f'hx-post="{self.url}"')
        self.assertContains(response, 'name="user_id" value="%s"' % self.alex.pk)
        self.assertContains(response, 'name="action" value="select"')
        self.assertContains(response, 'name="action" value="new"')
        # The clicked add button follows the hidden default action in form order.
        response = self.client.post(
            self.url, "action=select&search_query=Alex&action=new", content_type="application/x-www-form-urlencoded"
        )
        self.assertContains(response, "Add a person")
        self.assertEqual(response.context["state"]["search_context"], "Alex")

    def test_htmx_search_selection_returns_sign_in_fragments(self):
        response = self.client.post(self.url, {"action": "select", "user_id": self.jordan.pk}, HTTP_HX_REQUEST="true")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jordan Lee")
        self.assertContains(response, 'id="checkin-status" hx-swap-oob="true"')
        self.assertNotContains(response, '<main class="checkin">')
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.jordan).exists())

    def test_search_selection_without_htmx_still_redirects(self):
        response = self.post(action="select", user_id=self.jordan.pk)
        self.assertContains(self.follow_checkin_redirect(response), "Jordan Lee")

    def test_htmx_invalid_swipe_returns_error_fragment(self):
        response = self.client.post(self.url, {"action": "submit", "entry": ";bad"}, HTTP_HX_REQUEST="true")
        self.assertContains(response, "Card data was incomplete or invalid")
        self.assertNotContains(response, '<main class="checkin">')
        self.assertEqual(response.content.count(b'hx-swap-oob="true"'), 2)

    def test_pending_card_shows_one_merged_form(self):
        self.swipe("9999999999999999")
        response = self.post(action="submit", entry="Alex")
        self.assertNotContains(response, "CARD READ")
        self.assertNotContains(response, "Add a new person")
        self.assertNotContains(response, 'class="pending-actions"')
        self.assertContains(response, 'class="checkin-new" data-netid-form', count=1)
        self.assertContains(response, 'value="9999999999999999" disabled')
        self.assertContains(response, 'name="action" value="cancel"')
        self.assertFalse(Attendance.objects.filter(event=self.event, user=self.alex).exists())

    def test_live_search_does_not_process_card_data(self):
        response = self.client.get(self.search_url, {"entry": ";1234567890123456=000"})
        self.assertNotContains(response, "Alex Rivera")
        self.assertFalse(Attendance.objects.filter(event=self.event).exists())
        response = self.client.get(self.search_url, {"entry": "Alex;1234567890123456=000"})
        self.assertNotContains(response, "Alex Rivera")

    def test_live_search_is_flagged_and_requires_staff(self):
        with override_settings(FEATURE_FLAGS={**settings.FEATURE_FLAGS, "UNIFIED_EVENT_CHECK_IN": False}):
            self.assertEqual(self.client.get(self.search_url, {"entry": "Alex"}).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.search_url, {"entry": "Alex"}).status_code, 302)

    def test_unknown_card_replaces_existing_card_after_confirmation(self):
        self.swipe("9999999999999999")
        response = self.post(action="select", user_id=self.alex.pk)
        self.assertContains(response, "previously linked card")
        self.follow_checkin_redirect(self.confirm())
        self.alex.userprofile.refresh_from_db()
        self.assertEqual(self.alex.userprofile.comet_card_serial_number, "9999999999999999")
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.alex).exists())

    def test_correction_moves_card_and_removes_only_new_attendance(self):
        self.swipe()
        correction = self.post(action="correct")
        self.assertNotContains(correction, "CORRECT A CARD LINK")
        self.assertContains(correction, 'value="1234567890123456" disabled')
        self.assertContains(correction, 'placeholder="Search by name or Net ID..."')
        self.assertContains(correction, "data-netid-form data-card-correction")
        suggestions = self.client.get(self.netids_url, {"search_field": "first_name", "first_name": "Jordan"})
        self.assertContains(suggestions, "jxl240002")
        confirmation = self.post(action="select", user_id=self.jordan.pk, from_netid_form="1", net_id="jxl240002")
        self.assertContains(confirmation, 'value="1234567890123456" disabled')
        self.assertContains(confirmation, "Link card to Jordan Lee?")
        self.jordan.userprofile.refresh_from_db()
        self.assertIsNone(self.jordan.userprofile.comet_card_serial_number)
        self.assertFalse(Attendance.objects.filter(event=self.event, user=self.jordan).exists())
        self.follow_checkin_redirect(self.confirm())
        self.alex.userprofile.refresh_from_db()
        self.jordan.userprofile.refresh_from_db()
        self.assertIsNone(self.alex.userprofile.comet_card_serial_number)
        self.assertEqual(self.jordan.userprofile.comet_card_serial_number, "1234567890123456")
        self.assertFalse(Attendance.objects.filter(event=self.event, user=self.alex).exists())
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.jordan).exists())

    def test_correction_form_rejects_a_mismatched_selection(self):
        self.swipe()
        self.post(action="correct")
        response = self.post(action="select", user_id=self.jordan.pk, from_netid_form="1", net_id="axr240001")
        self.assertContains(response, "The selected person changed")
        self.assertContains(response, "Who does this card belong to?")
        self.jordan.userprofile.refresh_from_db()
        self.assertIsNone(self.jordan.userprofile.comet_card_serial_number)

    def test_correction_new_person_requires_confirmation_before_card_moves(self):
        self.swipe()
        self.post(action="correct")
        response = self.post(action="create", first_name="Sam", last_name="Smith", net_id="sam240001", major="")
        self.assertContains(response, "Link card to Sam Smith?")
        person = User.objects.get(username="sam240001")
        self.assertIsNone(person.userprofile.comet_card_serial_number)
        self.assertFalse(Attendance.objects.filter(event=self.event, user=person).exists())
        self.alex.userprofile.refresh_from_db()
        self.assertEqual(self.alex.userprofile.comet_card_serial_number, "1234567890123456")
        self.follow_checkin_redirect(self.confirm())
        person.userprofile.refresh_from_db()
        self.assertEqual(person.userprofile.comet_card_serial_number, "1234567890123456")
        self.assertTrue(Attendance.objects.filter(event=self.event, user=person).exists())

    def test_correction_preserves_preexisting_attendance(self):
        attendance = Attendance.objects.create(event=self.event, user=self.alex)
        self.swipe()
        self.post(action="correct")
        self.post(action="select", user_id=self.jordan.pk)
        self.confirm()
        self.assertTrue(Attendance.objects.filter(pk=attendance.pk).exists())

    def test_failed_confirmation_rolls_back_card_and_attendance_changes(self):
        self.swipe()
        self.post(action="correct")
        self.post(action="select", user_id=self.jordan.pk)
        with patch("events.unified_check_in._record_check_in", side_effect=IntegrityError):
            response = self.confirm()
        self.assertContains(response, "The card changed. Please swipe it again.")
        self.alex.userprofile.refresh_from_db()
        self.jordan.userprofile.refresh_from_db()
        self.assertEqual(self.alex.userprofile.comet_card_serial_number, "1234567890123456")
        self.assertIsNone(self.jordan.userprofile.comet_card_serial_number)
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.alex).exists())
        self.assertFalse(Attendance.objects.filter(event=self.event, user=self.jordan).exists())

    def test_create_requires_net_id_and_prevents_duplicates(self):
        self.swipe("9999999999999999")
        response = self.post(action="create", first_name="Sam", last_name="Smith", net_id="", major="")
        self.assertContains(response, "This field is required")
        response = self.post(action="create", first_name="Sam", last_name="Smith", net_id="AXR240001", major="")
        self.assertContains(response, "already exists")
        response = self.post(action="create", first_name="Sam", last_name="Smith", net_id="sam240001", major="")
        self.follow_checkin_redirect(response)
        user = User.objects.get(username="sam240001")
        self.assertTrue(Attendance.objects.filter(event=self.event, user=user).exists())
        self.assertEqual(user.userprofile.comet_card_serial_number, "9999999999999999")

    def test_staff_form_reuses_registration_fields_with_optional_major(self):
        staff_form = NewAttendeeForm({"net_id": "sam240001", "first_name": "Sam", "last_name": "Smith", "major": ""})
        self.assertIsInstance(staff_form, RegistrationCompletionForm)
        self.assertTrue(staff_form.is_valid(), staff_form.errors)
        self.assertEqual(list(staff_form.fields), ["net_id", "major", "first_name", "last_name"])
        self.assertNotIn("link_discord", staff_form.fields)
        registration_form = RegistrationCompletionForm(User(), {"first_name": "Sam", "last_name": "Smith", "major": ""})
        self.assertFalse(registration_form.is_valid())
        self.assertIn("major", registration_form.errors)

    def test_staff_form_still_accepts_unknown_major(self):
        form = NewAttendeeForm({"net_id": "sam240001", "first_name": "Sam", "last_name": "Smith", "major": "unknown"})
        self.assertTrue(form.is_valid(), form.errors)

    def test_stale_confirmation_cannot_move_card(self):
        self.swipe("9999999999999999")
        self.post(action="select", user_id=self.alex.pk)
        self.post(action="confirm", confirmation="stale")
        self.alex.userprofile.refresh_from_db()
        self.assertEqual(self.alex.userprofile.comet_card_serial_number, "1234567890123456")

    def test_changed_target_card_requires_another_swipe(self):
        self.swipe("9999999999999999")
        self.post(action="select", user_id=self.jordan.pk)
        self.jordan.userprofile.comet_card_serial_number = "1111111111111111"
        self.jordan.userprofile.save()
        response = self.confirm()
        self.assertContains(response, "card changed")
        self.jordan.userprofile.refresh_from_db()
        self.assertEqual(self.jordan.userprofile.comet_card_serial_number, "1111111111111111")

    def test_search_keeps_the_last_result_visible(self):
        self.swipe()
        response = self.post(action="submit", entry="Jordan")
        self.assertContains(response, "Signed in")
        self.assertContains(response, "Jordan Lee")
        self.assertContains(response, "Alex Rivera")

    def test_invalid_swipe_does_not_record_attendance(self):
        response = self.post(action="submit", entry=";123=oops")
        self.assertContains(response, "Card data was incomplete or invalid")
        self.assertFalse(Attendance.objects.filter(event=self.event).exists())

    def test_invalid_swipe_clears_previous_sign_in_result(self):
        self.client.post(
            self.url, {"action": "submit", "entry": ";1234567890123456=0000000000000000?"}, HTTP_HX_REQUEST="true"
        )
        response = self.client.post(self.url, {"action": "submit", "entry": ";123=oops"}, HTTP_HX_REQUEST="true")
        self.assertContains(response, "Card data was incomplete or invalid")
        self.assertNotContains(response, "Alex Rivera")
        self.assertNotIn("result", self.client.session[f"unified_check_in_{self.event.pk}"])
        self.assertTrue(Attendance.objects.filter(event=self.event, user=self.alex).exists())

    def test_requires_staff(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
