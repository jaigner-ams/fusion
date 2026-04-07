from django.db.models import Exists, OuterRef
from .models import Dentist, FileUpload, FileDownload


def lab_portal_context(request):
    """Provide sidebar context data and base template for all authenticated users."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'base_template': 'mgmt/base_portal.html',
        }

    ctx = {
        'base_template': 'mgmt/base_portal.html',
    }

    if request.user.has_role('lab'):
        ctx['dentist_count'] = Dentist.objects.filter(lab=request.user).count()
        # Count files this user hasn't downloaded yet
        ctx['pending_files_count'] = FileUpload.objects.filter(
            dentist__lab=request.user,
        ).exclude(
            downloads__user=request.user,
        ).count()
    elif request.user.has_role('admin'):
        ctx['dentist_count'] = Dentist.objects.count()
        ctx['pending_files_count'] = FileUpload.objects.exclude(
            downloads__user=request.user,
        ).count()

    return ctx
