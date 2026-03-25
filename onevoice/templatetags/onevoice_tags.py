from django import template

register = template.Library()


@register.filter
def ov_status_color(status):
    """Return CSS color class for dentist status."""
    colors = {
        'never_called': 'gray',
        'no_answer': 'yellow',
        'email_captured': 'blue',
        'called_no_email': 'orange',
        'appointment': 'green',
        'do_not_contact': 'red',
        'removed': 'gray',
    }
    return colors.get(status, 'gray')
