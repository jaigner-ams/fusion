from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.db import transaction
from django.contrib import messages
from .models import Dentist, DefaultPriceList, PriceList
from .forms import DentistForm, DefaultPriceForm, CustomPriceForm
from .decorators import lab_required

@login_required
@lab_required
def price_management_view(request):
    dentists = Dentist.objects.filter(lab=request.user)
    default_prices = DefaultPriceList.objects.filter(lab=request.user).order_by('applied_after')
    
    context = {
        'dentists': dentists,
        'default_prices': default_prices,
    }
    return render(request, 'mgmt/price_management.html', context)

@login_required
@lab_required
def default_prices_view(request):
    from django.forms import modelformset_factory
    
    DefaultPriceFormSet = modelformset_factory(
        model=DefaultPriceList,
        form=DefaultPriceForm,
        extra=1,
        can_delete=True,
        fields=['applied_after', 'price', 'type']
    )
    
    if request.method == 'POST':
        formset = DefaultPriceFormSet(request.POST, queryset=DefaultPriceList.objects.filter(lab=request.user))
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.lab = request.user
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, 'Default prices updated successfully!')
            return redirect('price_management')
    else:
        formset = DefaultPriceFormSet(queryset=DefaultPriceList.objects.filter(lab=request.user))
    
    context = {
        'formset': formset,
        'title': 'Manage Default Prices'
    }
    return render(request, 'mgmt/default_prices.html', context)

@login_required
@lab_required
def add_dentist_view(request):
    if request.method == 'POST':
        form = DentistForm(request.POST)
        if form.is_valid():
            dentist = form.save(commit=False)
            dentist.lab = request.user
            dentist.save()
            messages.success(request, f'Dentist {dentist.name} added successfully!')
            return redirect('dentist_prices', dentist_id=dentist.id)
    else:
        form = DentistForm()
    
    context = {
        'form': form,
        'title': 'Add New Dentist'
    }
    return render(request, 'mgmt/add_dentist.html', context)

@login_required
@lab_required
def dentist_prices_view(request, dentist_id):
    dentist = get_object_or_404(Dentist, id=dentist_id, lab=request.user)
    
    CustomPriceFormSet = inlineformset_factory(
        parent_model=Dentist,
        model=PriceList,
        form=CustomPriceForm,
        extra=1,
        can_delete=True,
        fields=['applied_after', 'price', 'type']
    )
    
    if request.method == 'POST':
        formset = CustomPriceFormSet(request.POST, instance=dentist)
        if formset.is_valid():
            formset.save()
            messages.success(request, f'Prices for {dentist.name} updated successfully!')
            return redirect('price_management')
    else:
        formset = CustomPriceFormSet(instance=dentist)
    
    default_prices = DefaultPriceList.objects.filter(lab=request.user).order_by('applied_after')
    
    context = {
        'formset': formset,
        'dentist': dentist,
        'default_prices': default_prices,
        'title': f'Manage Prices for {dentist.name}'
    }
    return render(request, 'mgmt/dentist_prices.html', context)

@login_required
@lab_required
def delete_dentist_view(request, dentist_id):
    dentist = get_object_or_404(Dentist, id=dentist_id, lab=request.user)
    
    if request.method == 'POST':
        name = dentist.name
        dentist.delete()
        messages.success(request, f'Dentist {name} deleted successfully!')
        return redirect('price_management')
    
    context = {
        'dentist': dentist,
        'title': f'Delete Dentist: {dentist.name}'
    }
    return render(request, 'mgmt/confirm_delete.html', context)
