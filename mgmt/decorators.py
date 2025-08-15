from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def lab_required(view_func):
    """
    Decorator to ensure only lab users can access the view
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if not request.user.is_lab_user():
            messages.error(request, 'You must be a lab user to access this page.')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper