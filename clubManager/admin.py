"""
Project-wide admin customizations.

Installed in place of ``django.contrib.admin`` in ``INSTALLED_APPS``, which is what lets the
tweaks below run *after* every app's ``admin`` module has been imported - including the ones in
third-party apps, which we would otherwise have no chance to adjust.

This module is the app config, so it is imported before the app registry is ready. Nothing
here may touch models at import time; those imports belong inside ``ready``.
"""

from django.contrib.admin.apps import AdminConfig


class ClubManagerAdminConfig(AdminConfig):
    def ready(self):
        # Runs django.contrib.admin's autodiscover, so everything is registered after this.
        super().ready()

        from django.contrib import admin
        from django.contrib.auth.models import User
        from post_office.models import EmailTemplate

        from common.admin import LowercaseUsernameUserAdmin

        # post_office can render mail from templates stored in the database, but we don't use
        # that: transactional mail is rendered from the Django templates in
        # core/templates/email/ by core.emails, so they can be reviewed and shipped alongside
        # the code that sends them. Leaving the EmailTemplate admin in place would offer
        # officers a template editor whose contents nothing ever reads, so hide it.
        #
        # Email, Log, and Attachment stay registered - those are the record of what we sent.
        admin.site.unregister(EmailTemplate)

        # Swap in a User admin that surfaces a duplicate Net ID as a field error rather than an
        # IntegrityError from the LOWER(username) unique index (issue #72). This has to happen
        # here rather than in an app's own admin module: those are imported *during*
        # autodiscover, and django.contrib.auth comes after them in INSTALLED_APPS, so our
        # registration would be overwritten by the stock one.
        admin.site.unregister(User)
        admin.site.register(User, LowercaseUsernameUserAdmin)
