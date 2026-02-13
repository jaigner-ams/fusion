from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a variable key."""
    if dictionary:
        return dictionary.get(key)
    return None


@register.filter
def get_zip_field(form, num):
    """Get a zip_protect_N field from a form."""
    field_name = f'zip_protect_{num}'
    if field_name in form.fields:
        return form[field_name]
    return ''


@register.filter
def get_qty_field(form, num):
    """Get a zip_qty_N field from a form."""
    field_name = f'zip_qty_{num}'
    if field_name in form.fields:
        return form[field_name]
    return ''