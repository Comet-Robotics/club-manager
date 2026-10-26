"""Template tags for static files.

``{% static_file %}`` behaves like ``{% static %}`` but appends the file's
modification time as a query string. Django serves static files in development
without a ``Cache-Control`` header, so browsers fall back to heuristic caching
and can keep using a stylesheet long after it changed — Safari is especially
stubborn about this. A new query string is a new URL, so an edited file is
always fetched while an unchanged one stays cached.
"""

import os

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()


@register.simple_tag
def static_file(path):
    url = static(path)
    source = finders.find(path)
    if not source:
        return url
    if isinstance(source, (list, tuple)):
        source = source[0]
    return f"{url}?v={int(os.path.getmtime(source))}"
