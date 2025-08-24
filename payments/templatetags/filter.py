from django import template

register = template.Library()


@register.filter
def cents_to_dollars(value):
    return "{:.2f}".format(value / 100)
