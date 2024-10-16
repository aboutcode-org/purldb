import json

from django import template

register = template.Library()


@register.filter(name="pretty_json")
def pretty_json(value):
    return json.dumps(value, indent=4)
