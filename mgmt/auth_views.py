from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib import messages
from django import forms
from django.views import View
from django.urls import reverse_lazy

class LabLoginForm(forms.Form):
    username = forms.CharField(
        label='Lab Login',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your lab login'})
    )
    password = forms.CharField(
        label='Lab Password', 
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your lab password'})
    )

class LabLoginView(View):
    template_name = 'registration/login.html'
    success_url = reverse_lazy('price_management')
    
    def get(self, request):
        form = LabLoginForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = LabLoginForm(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Authenticate using our custom backend
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome {user.first_name or username}!')
                
                # Handle next URL if provided
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect(self.success_url)
            else:
                messages.error(request, 'Invalid lab login or password.')
        
        return render(request, self.template_name, {'form': form})