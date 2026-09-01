from django import template

register = template.Library()


@register.filter(name='dict_lookup')
def dict_lookup(dictionary, key):
    """
    Look up a key in a dictionary dynamically in Django templates.
    Usage: {{ dictionary|dict_lookup:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
