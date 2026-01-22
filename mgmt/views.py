from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.forms import inlineformset_factory
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponse, FileResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
import os
from .models import Dentist, DefaultPriceList, PriceList, CreditPurchase, CreditTransaction, FileUpload, CustomUser
from .forms import DentistForm, DefaultPriceForm, CustomPriceForm, DentistWithUserForm, CreditPurchaseForm, CreditDeductionForm, DentistPasswordChangeForm, FileUploadForm, LabProfileForm
from .decorators import lab_required, lab_or_admin_required, dentist_required

def send_credit_purchase_notifications(purchase):
    """Send email notifications when a dentist purchases crown credits"""
    try:
        # Prepare email context
        context = {
            'lab_name': purchase.dentist.lab.first_name or purchase.dentist.lab.username,
            'lab_username': purchase.dentist.lab.username,
            'dentist_name': purchase.dentist.name,
            'dentist_username': purchase.user.username,
            'quantity': purchase.quantity,
            'quality_type': purchase.get_quality_type_display(),
            'unit_price': purchase.unit_price,
            'total_price': purchase.total_price,
            'purchase_date': purchase.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'status': purchase.get_status_display(),
            'purchase_id': purchase.id,
        }
        
        # Send notification to lab
        if purchase.dentist.lab.email:
            lab_subject = f'Crown Credit Purchase by {purchase.dentist.name}'
            lab_message = render_to_string('mgmt/emails/credit_purchase_lab_notification.html', context)
            
            send_mail(
                subject=lab_subject,
                message='',  # Plain text version (we're using HTML)
                html_message=lab_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[purchase.dentist.lab.email],
                fail_silently=False,
            )
        
        # Send notification to admin
        admin_subject = f'Crown Credit Purchase - {context["lab_name"]} - {purchase.dentist.name}'
        admin_message = render_to_string('mgmt/emails/credit_purchase_admin_notification.html', context)
        
        send_mail(
            subject=admin_subject,
            message='',  # Plain text version (we're using HTML)
            html_message=admin_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['jvonthaden@americasmiles.com'],
            fail_silently=False,
        )
        
        return True
        
    except Exception as e:
        # Log the error but don't fail the purchase
        print(f"Failed to send credit purchase notifications: {str(e)}")
        return False

@login_required
@lab_or_admin_required
def price_management_view(request):
    if request.user.is_admin_user():
        dentists = Dentist.objects.all()
        default_prices = DefaultPriceList.objects.all().order_by('lab', 'applied_after')
        lab_name = 'All Labs'
    else:
        dentists = Dentist.objects.filter(lab=request.user)
        default_prices = DefaultPriceList.objects.filter(lab=request.user).order_by('applied_after')
        lab_name = request.user.first_name or request.user.username
    
    context = {
        'dentists': dentists,
        'default_prices': default_prices,
        'lab_name': lab_name,
    }
    return render(request, 'mgmt/price_management.html', context)

@login_required
@lab_or_admin_required
def default_prices_view(request):
    from django.forms import modelformset_factory
    
    # Get lab name for display
    lab_name = request.user.first_name or request.user.username if request.user.user_type == 'lab' else 'Lab'
    
    # Create a custom form class that passes the user
    class DefaultPriceFormWithUser(DefaultPriceForm):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, user=request.user, **kwargs)
    
    if request.user.is_admin_user():
        fields = ['lab', 'is_cod', 'applied_after', 'price', 'type', 'product_description', 'notes']
    else:
        fields = ['is_cod', 'applied_after', 'price', 'type', 'product_description', 'notes']
    
    DefaultPriceFormSet = modelformset_factory(
        model=DefaultPriceList,
        form=DefaultPriceFormWithUser,
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
        'title': f'Manage {lab_name} Default Prices',
        'lab_name': lab_name
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
            
            # Check if credentials were auto-generated (for new dentists)
            if hasattr(dentist, '_generated_username') and hasattr(dentist, '_generated_password'):
                email_msg = ""
                if dentist.user and dentist.user.email and dentist.user.email != f"{dentist._generated_username}@dental-lab.com":
                    email_msg = f" An email with login credentials has been sent to {dentist.user.email}."
                
                messages.success(
                    request, 
                    f'Dentist {dentist.name} added successfully! '
                    f'Auto-generated login credentials: '
                    f'Username: {dentist._generated_username}, '
                    f'Password: {dentist._generated_password} '
                    f'(Please save these credentials securely){email_msg}'
                )
            elif dentist.user:
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
        fields=['is_cod', 'applied_after', 'price', 'type', 'product_description']
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
    
    # Get default prices from the lab, organized like the public page
    default_prices_qs = DefaultPriceList.objects.filter(lab=dentist.lab).order_by('product_description', 'applied_after')

    # Separate premium and economy prices, grouped by product description
    premium_prices = {}
    economy_prices = {}

    for price in default_prices_qs:
        if price.type == 'premium':
            key = price.product_description or 'Premium Crowns'
            if key not in premium_prices:
                premium_prices[key] = []
            premium_prices[key].append(price)
        else:
            key = 'Economy Crowns'
            if key not in economy_prices:
                economy_prices[key] = []
            economy_prices[key].append(price)

    # Sort economy prices by price descending (highest first)
    for key in economy_prices:
        economy_prices[key] = sorted(economy_prices[key], key=lambda x: x.price, reverse=True)

    has_default_prices = default_prices_qs.exists()

    # Get recent purchases
    recent_purchases = CreditPurchase.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]

    context = {
        'dentist': dentist,
        'custom_prices': custom_prices,
        'premium_prices': premium_prices,
        'economy_prices': economy_prices,
        'has_default_prices': has_default_prices,
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
            
            # Send email notifications to lab and admin
            send_credit_purchase_notifications(purchase)
            
            messages.success(request, f'Successfully purchased {purchase.quantity} crown credits for ${purchase.total_price}!')
            return redirect('dentist_dashboard')
    else:
        form = CreditPurchaseForm(dentist=dentist)
    
    # Get pricing tiers for display
    custom_prices = PriceList.objects.filter(dentist=dentist).order_by('type', 'applied_after')
    default_prices_qs = DefaultPriceList.objects.filter(lab=dentist.lab).order_by('product_description', 'applied_after')

    # Separate premium and economy prices, grouped by product description
    premium_prices = {}
    economy_prices = {}

    for price in default_prices_qs:
        if price.type == 'premium':
            key = price.product_description or 'Premium Crowns'
            if key not in premium_prices:
                premium_prices[key] = []
            premium_prices[key].append(price)
        else:
            key = 'Economy Crowns'
            if key not in economy_prices:
                economy_prices[key] = []
            economy_prices[key].append(price)

    # Sort economy prices by price descending (highest first)
    for key in economy_prices:
        economy_prices[key] = sorted(economy_prices[key], key=lambda x: x.price, reverse=True)

    has_default_prices = default_prices_qs.exists()

    # Get lab name for display
    lab_name = dentist.lab.first_name or dentist.lab.username

    context = {
        'form': form,
        'dentist': dentist,
        'custom_prices': custom_prices,
        'default_prices': default_prices_qs,  # Keep for JS price calculation
        'premium_prices': premium_prices,
        'economy_prices': economy_prices,
        'has_default_prices': has_default_prices,
        'current_credits': request.user.credits,
        'title': 'Purchase Crown Credits',
        'lab_name': lab_name
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
        'title': 'Crown Credit Purchase History'
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
        title = "All Crown Credit Purchases"
    else:
        # Lab users can only see their dentists' purchases
        dentists = Dentist.objects.filter(lab=request.user)
        purchases = CreditPurchase.objects.filter(dentist__in=dentists).order_by('-created_at')
        title = "Your Dentists' Crown Credit Purchases"
    
    # Calculate totals
    total_revenue = sum(p.total_price for p in purchases if p.status == 'completed')
    total_credits_sold = sum(p.quantity for p in purchases if p.status == 'completed')
    pending_purchases = purchases.filter(status='pending').count()
    
    # Calculate per-dentist statistics
    dentist_stats = {}
    for dentist in dentists:
        completed_purchases = CreditPurchase.objects.filter(
            dentist=dentist, 
            status='completed'
        )
        dentist_stats[dentist.id] = {
            'total_purchased': sum(p.quantity for p in completed_purchases),
            'total_spent': sum(p.total_price for p in completed_purchases)
        }
    
    context = {
        'purchases': purchases,
        'dentists': dentists,
        'dentist_stats': dentist_stats,
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
            messages.success(request, f'Purchase completed! {purchase.quantity} crown credits added to {purchase.user.first_name or purchase.user.username}.')
        elif purchase.status == 'completed':
            purchase.status = 'cancelled'
            purchase.save()
            # Remove credits from user
            purchase.user.credits = max(0, purchase.user.credits - purchase.quantity)
            purchase.user.save()
            messages.warning(request, f'Purchase cancelled. {purchase.quantity} crown credits removed from {purchase.user.first_name or purchase.user.username}.')
        
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
        messages.error(request, f'{dentist.name} does not have a user account. Cannot deduct crown credits.')
        return redirect('credit_management')
    
    if request.method == 'POST':
        form = CreditDeductionForm(request.POST, user=dentist.user, lab_user=request.user)
        if form.is_valid():
            transaction_obj = form.save()
            credit_type_display = transaction_obj.get_credit_type_display()
            messages.success(request, f'Successfully deducted {abs(transaction_obj.amount)} {credit_type_display} crown credits from {dentist.user.first_name or dentist.user.username}. New balance - Economy: {transaction_obj.economy_balance_after}, Premium: {transaction_obj.premium_balance_after}')
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
        'title': f'Deduct Crown Credits - {dentist.name}'
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
                f'Successfully undid deduction of {abs(transaction.amount)} crown credits. '
                f'{transaction.user.first_name or transaction.user.username} now has {reversal.balance_after} crown credits.'
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
        'title': f'Undo Crown Credit Deduction'
    }
    return render(request, 'mgmt/undo_deduction.html', context)

@login_required
@lab_or_admin_required
def credit_transactions_view(request):
    """View all credit transactions for lab's dentists"""
    if request.user.is_admin_user():
        transactions = CreditTransaction.objects.all()
        title = "All Crown Credit Transactions"
    else:
        # Lab users see transactions for their dentists only
        # Include transactions where dentist is None but user belongs to their dentists
        from django.db.models import Q
        transactions = CreditTransaction.objects.filter(
            Q(dentist__lab=request.user) | 
            Q(dentist__isnull=True, user__dentist_profile__lab=request.user)
        )
        title = "Crown Credit Transactions - Your Dentists"
    
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
def dentist_change_password_view(request):
    """Allow dentists to change their own password"""
    from django.contrib.auth.forms import PasswordChangeForm
    from django.contrib.auth import update_session_auth_hash
    
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Keep the user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been successfully changed!')
            return redirect('dentist_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    context = {
        'form': form,
        'title': 'Change Password'
    }
    return render(request, 'mgmt/dentist_change_password.html', context)

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
@lab_or_admin_required
def lab_upload_file_view(request):
    """Allow labs to upload files for their dentists"""
    if request.user.is_admin_user():
        # Admin can upload for any dentist
        dentists = Dentist.objects.all().order_by('name')
    else:
        # Lab can only upload for their dentists
        dentists = Dentist.objects.filter(lab=request.user).order_by('name')
    
    if request.method == 'POST':
        dentist_id = request.POST.get('dentist')
        if dentist_id:
            try:
                if request.user.is_admin_user():
                    dentist = Dentist.objects.get(id=dentist_id)
                else:
                    dentist = Dentist.objects.get(id=dentist_id, lab=request.user)
                
                form = FileUploadForm(request.POST, request.FILES, user=request.user, dentist=dentist)
                if form.is_valid():
                    upload = form.save()
                    messages.success(request, f'File "{upload.original_filename}" uploaded successfully for {dentist.name}!')
                    # Check if we should redirect back to lab uploads or file list
                    if 'upload_another' in request.POST:
                        return redirect('lab_upload_file')
                    else:
                        return redirect('lab_file_list')
                else:
                    messages.error(request, 'Please correct the errors below.')
            except Dentist.DoesNotExist:
                messages.error(request, 'Invalid dentist selected.')
                form = None
        else:
            messages.error(request, 'Please select a dentist.')
            form = None
    else:
        form = None
    
    context = {
        'form': form,
        'dentists': dentists,
        'title': 'Upload File for Dentist'
    }
    return render(request, 'mgmt/lab_upload_file.html', context)

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

@login_required
def stl_viewer(request):
    """View for displaying the STL viewer."""
    # Get recent STL files if user is lab or admin
    uploaded_files = []
    if request.user.user_type in ['lab', 'admin']:
        # Get recent STL files
        uploaded_files = FileUpload.objects.filter(
            file__iendswith='.stl'
        ).select_related('dentist').order_by('-uploaded_at')[:10]
    
    context = {
        'uploaded_files': uploaded_files,
    }
    
    return render(request, 'mgmt/stl_viewer.html', context)

@login_required
@lab_or_admin_required
def credit_deductions_view(request):
    """View all credit deductions with reasons"""
    from django.db.models import Q
    
    # Get deductions based on user type
    if request.user.is_admin_user():
        # Admin sees all deductions
        deductions = CreditTransaction.objects.filter(
            transaction_type='deduction'
        ).select_related('user', 'dentist', 'created_by').order_by('-created_at')
        title = "All Crown Credit Deductions"
    else:
        # Lab users see only their dentists' deductions
        deductions = CreditTransaction.objects.filter(
            Q(transaction_type='deduction') & 
            (Q(dentist__lab=request.user) | 
             Q(dentist__isnull=True, user__dentist_profile__lab=request.user))
        ).select_related('user', 'dentist', 'created_by').order_by('-created_at')
        title = "Crown Credit Deductions - Your Dentists"
    
    # Force evaluation of the queryset
    deductions = list(deductions)
    
    # Calculate totals
    total_deductions = abs(sum(d.amount for d in deductions))
    total_deduction_count = len(deductions)
    
    # Group deductions by dentist
    dentist_deductions = {}
    for deduction in deductions:
        dentist_name = deduction.dentist.name if deduction.dentist else (
            deduction.user.dentist_profile.name if hasattr(deduction.user, 'dentist_profile') else 
            f"{deduction.user.first_name} {deduction.user.last_name}".strip() or deduction.user.username
        )
        
        if dentist_name not in dentist_deductions:
            dentist_deductions[dentist_name] = {
                'deductions': [],
                'total': 0,
                'count': 0
            }
        
        dentist_deductions[dentist_name]['deductions'].append(deduction)
        dentist_deductions[dentist_name]['total'] += abs(deduction.amount)
        dentist_deductions[dentist_name]['count'] += 1
    
    context = {
        'deductions': deductions,
        'dentist_deductions': dentist_deductions,
        'total_deductions': total_deductions,
        'total_deduction_count': total_deduction_count,
        'title': title
    }

    return render(request, 'mgmt/credit_deductions.html', context)

@lab_or_admin_required
def lab_profile(request):
    """View for labs to edit their profile information"""
    if request.method == 'POST':
        form = LabProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lab profile updated successfully!')
            return redirect('lab_profile')
    else:
        form = LabProfileForm(instance=request.user)

    return render(request, 'mgmt/lab_profile.html', {'form': form})


def lab_public_page(request, username):
    """Public page for a lab showing their info and default prices"""
    lab = get_object_or_404(CustomUser, username=username, user_type='lab')

    # Get default prices for this lab
    default_prices = DefaultPriceList.objects.filter(lab=lab).order_by('product_description', 'applied_after')

    # Separate premium and economy prices, grouped by product description
    premium_prices = {}
    economy_prices = {}

    for price in default_prices:
        if price.type == 'premium':
            # Group by product description for premium
            key = price.product_description or 'Premium Crowns'
            if key not in premium_prices:
                premium_prices[key] = []
            premium_prices[key].append(price)
        else:
            # Group economy prices together
            key = 'Economy Crowns'
            if key not in economy_prices:
                economy_prices[key] = []
            economy_prices[key].append(price)

    # Sort economy prices by price descending (highest first)
    for key in economy_prices:
        economy_prices[key] = sorted(economy_prices[key], key=lambda x: x.price, reverse=True)

    context = {
        'lab': lab,
        'lab_name': lab.first_name or lab.username,
        'premium_prices': premium_prices,
        'economy_prices': economy_prices,
        'has_prices': default_prices.exists(),
    }

    return render(request, 'mgmt/lab_public.html', context)
