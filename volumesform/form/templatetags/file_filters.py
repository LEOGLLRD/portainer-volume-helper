from django import template
import os

register = template.Library()


@register.filter
def get_extension(value):
    name, ext = os.path.splitext(value["name"])
    return ext


@register.filter
def format_size(size):
    try:
        size = int(size)
        for unit in ['o', 'Ko', 'Mo', 'Go', 'To']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024.0
    except:
        return "?"
