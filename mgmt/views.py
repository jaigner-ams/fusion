from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.db import transaction
from django.contrib import messages
from .models import Dentist, DefaultPriceList, PriceList, CreditPurchase
from .forms import DentistForm, DefaultPriceForm, CustomPriceForm, DentistWithUserForm, CreditPurchaseForm
from .decorators import lab_required, lab_or_admin_required, dentist_required

@login_required
@lab_or_admin_required
def price_management_view(request):
    if request.user.is_admin_user():
        dentists = Dentist.objects.all()
        default_prices = DefaultPriceList.objects.all().order_by('lab', 'applied_after')
    else:
        dentists = Dentist.objects.filter(lab=request.user)
        default_prices = DefaultPriceList.objects.filter(lab=request.user).order_by('applied_after')
    
    context = {
        'dentists': dentists,
        'default_prices': default_prices,
    }
    return render(request, 'mgmt/price_management.html', context)

@login_required
@lab_or_admin_required
def default_prices_view(request):
    from django.forms import modelformset_factory
    
    if request.user.is_admin_user():
        fields = ['lab', 'applied_after', 'price', 'type']
    else:
        fields = ['applied_after', 'price', 'type']
    
    DefaultPriceFormSet = modelformset_factory(
        model=DefaultPriceList,
        form=DefaultPriceForm,
        extra=1,
        can_delete=True,
        fields=fields
    )
    
    if request.method == 'POST':
        if request.user.is_admin_user():
            formset = DefaultPriceFormSet(request.POST, queryset=DefaultPriceList.objects.all())
        else:
            formset = DefaultPriceFormSet(request.POST, queryset=DefaultPriceList.objects.filter(lab=request.user))
        
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                if not request.user.is_admin_user():
                    instance.lab = request.user
                instance.save()
            for obj in formset.deleted_objects:
                obj.delete()
            messages.success(request, 'Default prices updated successfully!')
            return redirect('price_management')
    else:
        if request.user.is_admin_user():
            formset = DefaultPriceFormSet(queryset=DefaultPriceList.objects.all())
        else:
            formset = DefaultPriceFormSet(queryset=DefaultPriceList.objects.filter(lab=request.user))
    
    context = {
        'formset': formset,
        'title': 'Manage Default Prices'
    }
    return render(request, 'mgmt/default_prices.html', context)

@login_required
@lab_or_admin_required
def add_dentist_view(request):
    if request.method == 'POST':
        form = DentistWithUserForm(request.POST, user=request.user)
        if form.is_valid():
            dentist = form.save(commit=False)
            if not request.user.is_admin_user():
                dentist.lab = request.user
            dentist.save()
            if dentist.user:
                messages.success(request, f'Dentist {dentist.name} added successfully with user account!')
            else:
                messages.success(request, f'Dentist {dentist.name} added successfully!')
            return redirect('dentist_prices', dentist_id=dentist.id)
    else:
        form = DentistWithUserForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Add New Dentist'
    }
    return render(request, 'mgmt/add_dentist.html', context)

@login_required
@lab_or_admin_required
def dentist_prices_view(request, dentist_id):
    if request.user.is_admin_user():
        dentist = get_object_or_404(Dentist, id=dentist_id)
    else:
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
    
    if request.user.is_admin_user():
        default_prices = DefaultPriceList.objects.filter(lab=dentist.lab).order_by('applied_after')
    else:
        default_prices = DefaultPriceList.objects.filter(lab=request.user).order_by('applied_after')
    
    context = {
        'formset': formset,
        'dentist': dentist,
        'default_prices': default_prices,
        'title': f'Manage Prices for {dentist.name}'
    }
    return render(request, 'mgmt/dentist_prices.html', context)

@login_required
@lab_or_admin_required
def edit_dentist_view(request, dentist_id):
    if request.user.is_admin_user():
        dentist = get_object_or_404(Dentist, id=dentist_id)
    else:
        dentist = get_object_or_404(Dentist, id=dentist_id, lab=request.user)
    
    if request.method == 'POST':
        form = DentistWithUserForm(request.POST, instance=dentist, user=request.user)
        if form.is_valid():
            dentist = form.save(commit=False)
            if not request.user.is_admin_user():
                dentist.lab = request.user
            dentist.save()
            messages.success(request, f'Dentist {dentist.name} updated successfully!')
            return redirect('price_management')
    else:
        form = DentistWithUserForm(instance=dentist, user=request.user)
    
    context = {
        'form': form,
        'dentist': dentist,
        'title': f'Edit Dentist: {dentist.name}'
    }
    return render(request, 'mgmt/edit_dentist.html', context)

@login_required
@lab_or_admin_required
def delete_dentist_view(request, dentist_id):
    if request.user.is_admin_user():
        dentist = get_object_or_404(Dentist, id=dentist_id)
    else:
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

@login_required
@dentist_required
def dentist_dashboard_view(request):
    """Dashboard for dentist users to view their information and prices"""
    try:
        dentist = request.user.dentist_profile
    except Dentist.DoesNotExist:
        messages.error(request, 'Your dentist profile was not found. Please contact your lab.')
        return redirect('login')
    
    # Get custom prices for this dentist
    custom_prices = PriceList.objects.filter(dentist=dentist).order_by('type', 'applied_after')
    
    # Get default prices from the lab
    default_prices = DefaultPriceList.objects.filter(lab=dentist.lab).order_by('type', 'applied_after')
    
    # Get recent purchases
    recent_purchases = CreditPurchase.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    context = {
        'dentist': dentist,
        'custom_prices': custom_prices,
        'default_prices': default_prices,
        'lab': dentist.lab,
        'credits': request.user.credits,
        'recent_purchases': recent_purchases,
        'title': f'Dashboard - {dentist.name}'
    }
    return render(request, 'mgmt/dentist_dashboard.html', context)

@login_required
@dentist_required
def purchase_credits_view(request):
    """Allow dentists to purchase credits"""
    try:
        dentist = request.user.dentist_profile
    except Dentist.DoesNotExist:
        messages.error(request, 'Your dentist profile was not found.')
        return redirect('dentist_dashboard')
    
    if request.method == 'POST':
        form = CreditPurchaseForm(request.POST, dentist=dentist)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.dentist = dentist
            purchase.user = request.user
            purchase.unit_price = purchase.calculate_price()
            purchase.total_price = purchase.unit_price * purchase.quantity
            
            if purchase.unit_price == 0:
                messages.error(request, 'No pricing configured for this purchase. Please contact your lab.')
                return redirect('purchase_credits')
            
            purchase.save()
            
            # For now, automatically complete the purchase (in real app, would integrate payment)
            purchase.complete_purchase()
            
            messages.success(request, f'Successfully purchased {purchase.quantity} credits for ${purchase.total_price}!')
            return redirect('dentist_dashboard')
    else:
        form = CreditPurchaseForm(dentist=dentist)
    
    # Get pricing tiers for display
    custom_prices = PriceList.objects.filter(dentist=dentist).order_by('type', 'applied_after')
    default_prices = DefaultPriceList.objects.filter(lab=dentist.lab).order_by('type', 'applied_after')
    
    context = {
        'form': form,
        'dentist': dentist,
        'custom_prices': custom_prices,
        'default_prices': default_prices,
        'current_credits': request.user.credits,
        'title': 'Purchase Credits'
    }
    return render(request, 'mgmt/purchase_credits.html', context)

@login_required
@dentist_required
def purchase_history_view(request):
    """View purchase history for dentist"""
    try:
        dentist = request.user.dentist_profile
    except Dentist.DoesNotExist:
        messages.error(request, 'Your dentist profile was not found.')
        return redirect('dentist_dashboard')
    
    purchases = CreditPurchase.objects.filter(user=request.user).order_by('-created_at')
    
    # Calculate totals
    total_credits = sum(p.quantity for p in purchases if p.status == 'completed')
    total_spent = sum(p.total_price for p in purchases if p.status == 'completed')
    
    context = {
        'purchases': purchases,
        'total_credits': total_credits,
        'total_spent': total_spent,
        'current_credits': request.user.credits,
        'title': 'Purchase History'
    }
    return render(request, 'mgmt/purchase_history.html', context)

@login_required
@lab_or_admin_required
def credit_management_view(request):
    """Allow labs and admins to view and manage credit purchases"""
    if request.user.is_admin_user():
        # Admin can see all purchases
        purchases = CreditPurchase.objects.all().order_by('-created_at')
        dentists = Dentist.objects.all()
        title = "All Credit Purchases"
    else:
        # Lab users can only see their dentists' purchases
        dentists = Dentist.objects.filter(lab=request.user)
        purchases = CreditPurchase.objects.filter(dentist__in=dentists).order_by('-created_at')
        title = "Your Dentists' Credit Purchases"
    
    # Calculate totals
    total_revenue = sum(p.total_price for p in purchases if p.status == 'completed')
    total_credits_sold = sum(p.quantity for p in purchases if p.status == 'completed')
    pending_purchases = purchases.filter(status='pending').count()
    
    context = {
        'purchases': purchases,
        'dentists': dentists,
        'total_revenue': total_revenue,
        'total_credits_sold': total_credits_sold,
        'pending_purchases': pending_purchases,
        'title': title
    }
    return render(request, 'mgmt/credit_management.html', context)

@login_required
@lab_or_admin_required
def toggle_purchase_status(request, purchase_id):
    """Toggle purchase status between pending and completed"""
    if request.user.is_admin_user():
        purchase = get_object_or_404(CreditPurchase, id=purchase_id)
    else:
        # Lab users can only manage their dentists' purchases
        purchase = get_object_or_404(CreditPurchase, id=purchase_id, dentist__lab=request.user)
    
    if request.method == 'POST':
        if purchase.status == 'pending':
            purchase.complete_purchase()
            messages.success(request, f'Purchase completed! {purchase.quantity} credits added to {purchase.user.first_name or purchase.user.username}.')
        elif purchase.status == 'completed':
            purchase.status = 'cancelled'
            purchase.save()
            # Remove credits from user
            purchase.user.credits = max(0, purchase.user.credits - purchase.quantity)
            purchase.user.save()
            messages.warning(request, f'Purchase cancelled. {purchase.quantity} credits removed from {purchase.user.first_name or purchase.user.username}.')
        
        return redirect('credit_management')
    
    return redirect('credit_management')
