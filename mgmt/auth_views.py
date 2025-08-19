from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
from django.views import View
from django.urls import reverse_lazy

class UniversalLoginForm(forms.Form):
    username = forms.CharField(
        label='Username',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your username'})
    )
    password = forms.CharField(
        label='Password', 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'})
    )

class LabLoginForm(UniversalLoginForm):
    """Kept for backward compatibility"""
    pass

class UniversalLoginView(View):
    template_name = 'registration/login.html'
    
    def get_success_url(self, user):
        """Redirect based on user type"""
        if user.is_admin_user() or user.is_lab_user():
            return reverse_lazy('price_management')
        elif user.is_dentist_user():
            return reverse_lazy('dentist_dashboard')
        else:
            return reverse_lazy('price_management')
    
    def get(self, request):
        form = UniversalLoginForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = UniversalLoginForm(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Authenticate using our custom backend
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Custom welcome message based on user type
                if user.is_admin_user():
                    messages.success(request, f'Welcome Admin {user.first_name or username}!')
                elif user.is_lab_user():
                    messages.success(request, f'Welcome {user.first_name or username}!')
                elif user.is_dentist_user():
                    messages.success(request, f'Welcome Dr. {user.first_name or username}!')
                else:
                    messages.success(request, f'Welcome {user.first_name or username}!')
                
                # Handle next URL if provided
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect(self.get_success_url(user))
            else:
                messages.error(request, 'Invalid username or password.')
        
        return render(request, self.template_name, {'form': form})

# Keep old class name for compatibility
class LabLoginView(UniversalLoginView):
    """Kept for backward compatibility"""
    pass

class CustomLogoutView(View):
    """Custom logout view with proper redirect and message"""
    
    def get(self, request):
        return self.logout_user(request)
    
    def post(self, request):
        return self.logout_user(request)
    
    def logout_user(self, request):
        from django.contrib.auth import logout
        
        if request.user.is_authenticated:
            username = request.user.username
            user_type = request.user.user_type if hasattr(request.user, 'user_type') else 'user'
            logout(request)
            messages.success(request, f'You have been successfully logged out. Thank you for using the system!')
        
        return redirect('login')