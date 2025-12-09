from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    """
    Replace underscores with spaces.
    Usage: {{ value|replace:"_" }}
    """
    if not value:
        return value
    # Simply replace underscores with spaces
    return str(value).replace("_", " ")

