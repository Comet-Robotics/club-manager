"""
Project-wide admin customizations.

Installed in place of ``django.contrib.admin`` in ``INSTALLED_APPS``, which is what lets the
tweaks below run *after* every app's ``admin`` module has been imported - including the ones in
third-party apps, which we would otherwise have no chance to adjust.
"""

from django.contrib.admin.apps import AdminConfig


class ClubManagerAdminConfig(AdminConfig):
    def ready(self):
        # Runs django.contrib.admin's autodiscover, so everything is registered after this.
        super().ready()

        from django.contrib import admin
        from post_office.models import EmailTemplate

        # post_office can render mail from templates stored in the database, but we don't use
        # that: transactional mail is rendered from the Django templates in
        # core/templates/email/ by core.emails, so they can be reviewed and shipped alongside
        # the code that sends them. Leaving the EmailTemplate admin in place would offer
        # officers a template editor whose contents nothing ever reads, so hide it.
        #
        # Email, Log, and Attachment stay registered - those are the record of what we sent.
        admin.site.unregister(EmailTemplate)
