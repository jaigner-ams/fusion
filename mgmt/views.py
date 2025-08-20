from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
import os
from .models import Dentist, DefaultPriceList, PriceList, CreditPurchase, CreditTransaction, FileUpload
from .forms import DentistForm, DefaultPriceForm, CustomPriceForm, DentistWithUserForm, CreditPurchaseForm, CreditDeductionForm, DentistPasswordChangeForm, FileUploadForm
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
            # Handle formset errors here if needed
            messages.error(request, 'Please correct the errors below.')
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
            # Handle formset errors here if needed
            messages.error(request, 'Please correct the errors below.')
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

@login_required
@lab_or_admin_required
def deduct_credits_view(request, dentist_id):
    """Allow lab users to deduct credits from dentists"""
    if request.user.is_admin_user():
        dentist = get_object_or_404(Dentist, id=dentist_id)
    else:
        dentist = get_object_or_404(Dentist, id=dentist_id, lab=request.user)
    
    if not dentist.user:
        messages.error(request, f'{dentist.name} does not have a user account. Cannot deduct credits.')
        return redirect('credit_management')
    
    if request.method == 'POST':
        form = CreditDeductionForm(request.POST, user=dentist.user, lab_user=request.user)
        if form.is_valid():
            transaction_obj = form.save()
            messages.success(request, f'Successfully deducted {abs(transaction_obj.amount)} credits from {dentist.user.first_name or dentist.user.username}. New balance: {transaction_obj.balance_after} credits.')
            return redirect('credit_management')
    else:
        form = CreditDeductionForm(user=dentist.user, lab_user=request.user)
    
    # Get recent transactions for this user
    recent_transactions = CreditTransaction.objects.filter(user=dentist.user).order_by('-created_at')[:10]
    
    context = {
        'form': form,
        'dentist': dentist,
        'user_to_deduct': dentist.user,
        'recent_transactions': recent_transactions,
        'title': f'Deduct Credits - {dentist.name}'
    }
    return render(request, 'mgmt/deduct_credits.html', context)

@login_required
@lab_or_admin_required
def undo_deduction_view(request, transaction_id):
    """Allow lab users to undo credit deductions"""
    # Get the transaction with better error handling
    try:
        if request.user.is_admin_user():
            transaction = CreditTransaction.objects.get(id=transaction_id)
        else:
            # Lab users can only undo deductions for their dentists
            # Include transactions where dentist is None but user belongs to their dentists
            from django.db.models import Q
            transaction = CreditTransaction.objects.get(
                Q(id=transaction_id) & 
                (Q(dentist__lab=request.user) | 
                 Q(dentist__isnull=True, user__dentist_profile__lab=request.user))
            )
    except CreditTransaction.DoesNotExist:
        messages.error(request, f'Transaction #{transaction_id} not found or you do not have permission to access it.')
        return redirect('credit_management')
    
    # Check if transaction can be reversed
    if not transaction.can_be_reversed():
        messages.error(request, 'This transaction cannot be undone. It may have already been reversed or is not a deduction.')
        return redirect('credit_management')
    
    if request.method == 'POST':
        try:
            # Create reversal transaction
            reversal = transaction.reverse_transaction(
                reversed_by_user=request.user,
                reason=f"Undo deduction requested by {request.user.username}"
            )
            messages.success(
                request, 
                f'Successfully undid deduction of {abs(transaction.amount)} credits. '
                f'{transaction.user.first_name or transaction.user.username} now has {reversal.balance_after} credits.'
            )
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('credit_management')
    
    # Calculate values for display
    credits_to_add_back = abs(transaction.amount)  # Convert negative to positive
    new_balance = transaction.user.credits + credits_to_add_back
    
    context = {
        'transaction': transaction,
        'credits_to_add_back': credits_to_add_back,
        'new_balance': new_balance,
        'title': f'Undo Credit Deduction'
    }
    return render(request, 'mgmt/undo_deduction.html', context)

@login_required
@lab_or_admin_required
def credit_transactions_view(request):
    """View all credit transactions for lab's dentists"""
    if request.user.is_admin_user():
        transactions = CreditTransaction.objects.all()
        title = "All Credit Transactions"
    else:
        # Lab users see transactions for their dentists only
        # Include transactions where dentist is None but user belongs to their dentists
        from django.db.models import Q
        transactions = CreditTransaction.objects.filter(
            Q(dentist__lab=request.user) | 
            Q(dentist__isnull=True, user__dentist_profile__lab=request.user)
        )
        title = "Credit Transactions - Your Dentists"
    
    transactions = transactions.select_related('user', 'dentist', 'created_by', 'reversed_by').order_by('-created_at')
    
    context = {
        'transactions': transactions,
        'title': title
    }
    return render(request, 'mgmt/credit_transactions.html', context)

@login_required
@lab_or_admin_required
def change_dentist_password_view(request, dentist_id):
    """Allow lab users to change dentist passwords"""
    if request.user.is_admin_user():
        dentist = get_object_or_404(Dentist, id=dentist_id)
    else:
        dentist = get_object_or_404(Dentist, id=dentist_id, lab=request.user)
    
    if not dentist.user:
        messages.error(request, f'{dentist.name} does not have a user account. Cannot change password.')
        return redirect('price_management')
    
    if request.method == 'POST':
        form = DentistPasswordChangeForm(request.POST, user=dentist.user, lab_user=request.user)
        if form.is_valid():
            try:
                form.save()
                messages.success(
                    request, 
                    f'Successfully changed password for {dentist.user.first_name or dentist.user.username}. '
                    f'They should use their new password for the next login.'
                )
                return redirect('price_management')
            except Exception as e:
                messages.error(request, f'Error changing password: {str(e)}')
    else:
        form = DentistPasswordChangeForm(user=dentist.user, lab_user=request.user)
    
    context = {
        'form': form,
        'dentist': dentist,
        'user_to_change': dentist.user,
        'title': f'Change Password - {dentist.name}'
    }
    return render(request, 'mgmt/change_dentist_password.html', context)

@login_required
@dentist_required
def upload_file_view(request):
    dentist = get_object_or_404(Dentist, user=request.user)
    
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES, user=request.user, dentist=dentist)
        if form.is_valid():
            upload = form.save()
            messages.success(request, f'File "{upload.original_filename}" uploaded successfully!')
            return redirect('dentist_file_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FileUploadForm(user=request.user, dentist=dentist)
    
    context = {
        'form': form,
        'title': 'Upload File for Lab'
    }
    return render(request, 'mgmt/upload_file.html', context)

@login_required
@dentist_required
def dentist_file_list_view(request):
    dentist = get_object_or_404(Dentist, user=request.user)
    files = FileUpload.objects.filter(dentist=dentist).order_by('-uploaded_at')
    
    context = {
        'files': files,
        'title': 'My Uploaded Files'
    }
    return render(request, 'mgmt/dentist_file_list.html', context)

@login_required
@lab_or_admin_required
def lab_file_list_view(request):
    if request.user.is_admin_user():
        files = FileUpload.objects.all().order_by('-uploaded_at')
    else:
        files = FileUpload.objects.filter(lab=request.user).order_by('-uploaded_at')
    
    context = {
        'files': files,
        'title': 'Files from Dentists'
    }
    return render(request, 'mgmt/lab_file_list.html', context)

@login_required
@lab_or_admin_required
def download_file_view(request, file_id):
    file_upload = get_object_or_404(FileUpload, id=file_id)
    
    # Check permissions
    if not request.user.is_admin_user() and file_upload.lab != request.user:
        messages.error(request, 'You do not have permission to download this file.')
        return redirect('lab_file_list')
    
    # Mark as downloaded
    file_upload.mark_as_downloaded(request.user)
    
    # Serve the file
    if os.path.exists(file_upload.file.path):
        response = FileResponse(open(file_upload.file.path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{file_upload.original_filename}"'
        return response
    else:
        messages.error(request, 'File not found on server.')
        return redirect('lab_file_list')
