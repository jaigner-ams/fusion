from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def ov_admin_required(view_func):
    """Restrict to OV Admin or Super Admin."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_ov_admin_user() or request.user.is_superadmin_user()):
            messages.error(request, 'You must be a One Voice admin to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def csr_required(view_func):
    """Restrict to CSR, OV Admin, or Super Admin."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_csr_user() or request.user.is_ov_admin_user() or request.user.is_superadmin_user()):
            messages.error(request, 'You must be a CSR to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def designer_required(view_func):
    """Restrict to Designer, OV Admin, or Super Admin."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_designer_user() or request.user.is_ov_admin_user() or request.user.is_superadmin_user()):
            messages.error(request, 'You must be a designer to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def ov_client_required(view_func):
    """Restrict to OV Client or Super Admin."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_ov_client_user() or request.user.is_superadmin_user()):
            messages.error(request, 'You must be a One Voice client to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def ov_staff_required(view_func):
    """Restrict to any OV staff role (not client)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_superadmin_user() or request.user.is_ov_admin_user()
                or request.user.is_csr_user() or request.user.is_designer_user()):
            messages.error(request, 'You must be One Voice staff to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
