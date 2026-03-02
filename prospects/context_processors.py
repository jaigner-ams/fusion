from .models import Mailer


def nav_mailers(request):
    """Provide mailer list for navigation dropdown"""
    if request.user.is_authenticated and hasattr(request.user, 'is_caller_user') and request.user.is_caller_user():
        return {'nav_mailers': Mailer.objects.all()[:20]}
    return {'nav_mailers': []}
