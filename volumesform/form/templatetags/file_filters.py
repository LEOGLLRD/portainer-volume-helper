from django import template
import os

register = template.Library()


@register.filter
def get_extension(value):
    name, ext = os.path.splitext(value["name"])
    return ext
