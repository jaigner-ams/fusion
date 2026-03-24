from .models import Dentist, FileUpload


def lab_portal_context(request):
    """Provide sidebar context data and base template for all authenticated users."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'base_template': 'mgmt/base_portal.html',
        }

    ctx = {
        'base_template': 'mgmt/base_portal.html',
    }

    if request.user.user_type == 'lab':
        ctx['dentist_count'] = Dentist.objects.filter(lab=request.user).count()
        ctx['pending_files_count'] = FileUpload.objects.filter(
            dentist__lab=request.user, status='pending'
        ).count()
    elif request.user.user_type == 'admin':
        ctx['dentist_count'] = Dentist.objects.count()
        ctx['pending_files_count'] = FileUpload.objects.filter(status='pending').count()

    return ctx
