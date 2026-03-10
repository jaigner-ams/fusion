import csv
import random
import string
from datetime import date, datetime

# Word lists for generating memorable passwords
PASSWORD_ADJECTIVES = [
    'Happy', 'Sunny', 'Blue', 'Green', 'Golden', 'Silver', 'Bright', 'Swift',
    'Lucky', 'Calm', 'Cool', 'Warm', 'Fresh', 'Bold', 'Kind', 'Quick'
]
PASSWORD_NOUNS = [
    'Tiger', 'Eagle', 'River', 'Mountain', 'Forest', 'Ocean', 'Star', 'Moon',
    'Cloud', 'Stone', 'Crown', 'Bridge', 'Garden', 'Meadow', 'Valley', 'Lake'
]

def generate_simple_password():
    """Generate a memorable password like 'HappyTiger42'"""
    adjective = random.choice(PASSWORD_ADJECTIVES)
    noun = random.choice(PASSWORD_NOUNS)
    number = random.randint(10, 99)
    return f"{adjective}{noun}{number}"
from urllib.parse import urlencode
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Prospect, ProspectNote, ProspectServiceType, Mailer, LeadReferral
from .forms import (ProspectForm, ProspectNoteForm, NextContactDateForm, CreateLabAccountForm,
                     CallerCallbackForm, CallerSentToKeithForm, CallerNotInterestedForm,
                     CallerLeftVoicemailForm, CallerEditReferralForm, CallerEditNoteForm)
from mgmt.models import CustomUser
from mgmt.decorators import caller_required


@login_required
def prospect_list(request):
    """List all prospects with status and AMS history filters"""
    if request.user.is_caller_user():
        return redirect('prospects:caller_dashboard')

    status_filter = request.GET.get('status', '')
    ams_history_filter = request.GET.get('ams_history', '')
    source_filter = request.GET.get('source', '')

    # Exclude caller-only statuses from Keith's list (until sent to him)
    caller_only_statuses = ['mailed', 'callback', 'not_interested', 'left_voicemail']
    prospects = Prospect.objects.exclude(status__in=caller_only_statuses)

    if source_filter == 'caller':
        prospects = prospects.filter(status__in=['sent_to_keith', 'keith_closed'])
    if status_filter:
        prospects = prospects.filter(status=status_filter)
    if ams_history_filter:
        prospects = prospects.filter(ams_history=ams_history_filter)

    # Count by status for dashboard (only statuses visible to Keith)
    keith_prospects = Prospect.objects.exclude(status__in=caller_only_statuses)
    caller_leads_count = keith_prospects.filter(status__in=['sent_to_keith', 'keith_closed']).count()
    status_counts = {
        'prospect': keith_prospects.filter(status='prospect').count(),
        'member': keith_prospects.filter(status='member').count(),
        'declined': keith_prospects.filter(status='declined').count(),
        'corporate': keith_prospects.filter(status='corporate').count(),
        'sent_to_keith': keith_prospects.filter(status='sent_to_keith').count(),
        'keith_closed': keith_prospects.filter(status='keith_closed').count(),
        'total': keith_prospects.count(),
    }

    # Build filter query string for preserving filters through navigation
    filter_params = {}
    if status_filter:
        filter_params['status'] = status_filter
    if ams_history_filter:
        filter_params['ams_history'] = ams_history_filter
    if source_filter:
        filter_params['source'] = source_filter
    filter_querystring = '?' + urlencode(filter_params) if filter_params else ''

    context = {
        'prospects': prospects,
        'status_filter': status_filter,
        'ams_history_filter': ams_history_filter,
        'source_filter': source_filter,
        'filter_querystring': filter_querystring,
        'status_choices': Prospect.STATUS_CHOICES,
        'ams_history_choices': Prospect.AMS_HISTORY_CHOICES,
        'status_counts': status_counts,
        'caller_leads_count': caller_leads_count,
        'title': 'Prospects List'
    }
    return render(request, 'prospects/prospect_list.html', context)


@login_required
def prospect_add(request):
    """Add a new prospect"""
    if request.user.is_caller_user():
        return redirect('prospects:caller_dashboard')
    if request.method == 'POST':
        form = ProspectForm(request.POST)
        if form.is_valid():
            prospect = form.save()
            # Handle service types
            service_types = request.POST.getlist('service_types')
            for st in service_types:
                ProspectServiceType.objects.create(prospect=prospect, service_type=st)
            messages.success(request, f'Prospect "{prospect.lab_name}" added successfully!')
            return redirect('prospects:prospect_detail', pk=prospect.pk)
    else:
        form = ProspectForm()

    context = {
        'form': form,
        'title': 'Add New Prospect'
    }
    return render(request, 'prospects/prospect_form.html', context)


@login_required
def prospect_edit(request, pk):
    """Edit an existing prospect"""
    if request.user.is_caller_user():
        return redirect('prospects:caller_edit', pk=pk)
    prospect = get_object_or_404(Prospect, pk=pk)

    # Preserve list filters for navigation
    filter_params = {}
    for key in ('status', 'ams_history', 'source'):
        val = request.GET.get(key, '')
        if val:
            filter_params[key] = val
    filter_querystring = '?' + urlencode(filter_params) if filter_params else ''

    if request.method == 'POST':
        form = ProspectForm(request.POST, instance=prospect)
        if form.is_valid():
            prospect = form.save()
            # Update service types
            prospect.service_types.all().delete()
            service_types = request.POST.getlist('service_types')
            for st in service_types:
                ProspectServiceType.objects.create(prospect=prospect, service_type=st)
            messages.success(request, f'Prospect "{prospect.lab_name}" updated successfully!')
            detail_url = reverse('prospects:prospect_detail', args=[prospect.pk])
            return redirect(detail_url + filter_querystring)
    else:
        form = ProspectForm(instance=prospect)
        # Pre-populate service types
        form.initial['service_types'] = list(
            prospect.service_types.values_list('service_type', flat=True)
        )

    context = {
        'form': form,
        'prospect': prospect,
        'filter_querystring': filter_querystring,
        'title': f'Edit Prospect: {prospect.lab_name}'
    }
    return render(request, 'prospects/prospect_form.html', context)


@login_required
def prospect_detail(request, pk):
    """View prospect details with notes"""
    if request.user.is_caller_user():
        return redirect('prospects:caller_detail', pk=pk)
    prospect = get_object_or_404(Prospect, pk=pk)
    notes = prospect.notes.all()
    note_form = ProspectNoteForm()
    date_form = NextContactDateForm(instance=prospect)

    # Preserve list filters for navigation
    filter_params = {}
    for key in ('status', 'ams_history', 'source'):
        val = request.GET.get(key, '')
        if val:
            filter_params[key] = val
    filter_querystring = '?' + urlencode(filter_params) if filter_params else ''

    if request.method == 'POST':
        if 'add_note' in request.POST:
            note_form = ProspectNoteForm(request.POST)
            if note_form.is_valid():
                note = note_form.save(commit=False)
                note.prospect = prospect
                note.created_by = request.user
                note.save()
                messages.success(request, 'Note added successfully!')
                detail_url = reverse('prospects:prospect_detail', args=[pk])
                return redirect(detail_url + filter_querystring)
        elif 'update_date' in request.POST:
            date_form = NextContactDateForm(request.POST, instance=prospect)
            if date_form.is_valid():
                date_form.save()
                messages.success(request, 'Next contact date updated!')
                detail_url = reverse('prospects:prospect_detail', args=[pk])
                return redirect(detail_url + filter_querystring)

    context = {
        'prospect': prospect,
        'notes': notes,
        'note_form': note_form,
        'date_form': date_form,
        'filter_querystring': filter_querystring,
        'title': f'Prospect: {prospect.lab_name}'
    }
    return render(request, 'prospects/prospect_detail.html', context)


@login_required
def prospect_delete(request, pk):
    """Delete a prospect"""
    if request.user.is_caller_user():
        return redirect('prospects:caller_dashboard')
    prospect = get_object_or_404(Prospect, pk=pk)

    if request.method == 'POST':
        lab_name = prospect.lab_name
        prospect.delete()
        messages.success(request, f'Prospect "{lab_name}" deleted successfully!')
        return redirect('prospects:prospect_list')

    context = {
        'prospect': prospect,
        'title': f'Delete Prospect: {prospect.lab_name}'
    }
    return render(request, 'prospects/prospect_confirm_delete.html', context)


@login_required
def prospect_print(request, pk):
    """Print-friendly view for prospects (excludes notes)"""
    prospect = get_object_or_404(Prospect, pk=pk)

    context = {
        'prospect': prospect,
        'title': f'Print: {prospect.lab_name}'
    }
    return render(request, 'prospects/prospect_print.html', context)


@login_required
def contact_schedule(request):
    """View prospects scheduled for contact on a specific date"""
    contact_date = request.GET.get('date', '')

    if contact_date:
        try:
            selected_date = date.fromisoformat(contact_date)
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    prospects = Prospect.objects.filter(next_contact_date=selected_date)

    context = {
        'prospects': prospects,
        'selected_date': selected_date,
        'title': f'Contacts for {selected_date.strftime("%B %d, %Y")}'
    }
    return render(request, 'prospects/contact_schedule.html', context)


@login_required
def export_csv(request):
    """Export prospects to CSV file"""
    status_filter = request.GET.get('status', '')
    ams_history_filter = request.GET.get('ams_history', '')
    contact_date = request.GET.get('contact_date', '')

    prospects = Prospect.objects.all()
    if status_filter:
        prospects = prospects.filter(status=status_filter)
    if ams_history_filter:
        prospects = prospects.filter(ams_history=ams_history_filter)
    if contact_date:
        try:
            selected_date = date.fromisoformat(contact_date)
            prospects = prospects.filter(next_contact_date=selected_date)
        except ValueError:
            pass

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    filename = f'prospects_{date.today().isoformat()}'
    if status_filter:
        filename += f'_{status_filter}'
    if ams_history_filter:
        filename += f'_{ams_history_filter}'
    if contact_date:
        filename += f'_contacts_{contact_date}'
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

    writer = csv.writer(response)

    # Write header row
    writer.writerow([
        'AMS History',
        'Status',
        'Lab Name',
        'Person Name',
        'Phone',
        'Email',
        'Address',
        'City',
        'State',
        'Zip Code',
        'Monthly Fee',
        'Has Mill',
        'Dentists Requested',
        'Service Types',
        'Protected Zip Codes',
        'Next Contact Date',
        'Created Date',
        'Last Updated',
    ])

    # Write data rows
    for prospect in prospects:
        writer.writerow([
            prospect.get_ams_history_display() if prospect.ams_history else '',
            prospect.get_status_display(),
            prospect.lab_name,
            prospect.person_name,
            prospect.phone,
            prospect.email,
            prospect.address,
            prospect.city,
            prospect.state,
            prospect.zip_code,
            prospect.monthly_fee or '',
            'Yes' if prospect.has_mill else 'No',
            prospect.dentists_requested or '',
            prospect.get_service_types_display(),
            ', '.join(prospect.get_protected_zip_codes()),
            prospect.next_contact_date.isoformat() if prospect.next_contact_date else '',
            prospect.created_at.strftime('%Y-%m-%d'),
            prospect.updated_at.strftime('%Y-%m-%d'),
        ])

    return response


@login_required
def create_lab_account(request, pk):
    """Create a lab user account for a prospect who has become a member"""
    prospect = get_object_or_404(Prospect, pk=pk)

    # Check if prospect is already a member with an account
    if prospect.lab_user:
        messages.warning(request, f'A lab account already exists for "{prospect.lab_name}".')
        return redirect('prospects:prospect_detail', pk=pk)

    # Check if prospect status is 'member'
    if prospect.status != 'member':
        messages.error(request, 'Can only create accounts for Fusion Members. Please change the status first.')
        return redirect('prospects:prospect_detail', pk=pk)

    if request.method == 'POST':
        form = CreateLabAccountForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            send_email = form.cleaned_data['send_email']

            # Check if username already exists
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, f'Username "{username}" already exists. Please choose a different username.')
                return render(request, 'prospects/create_lab_account.html', {
                    'form': form,
                    'prospect': prospect,
                    'title': f'Create Account for {prospect.lab_name}'
                })

            # Generate a memorable password
            password = generate_simple_password()

            # Create the lab user account
            lab_user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type='lab',
                first_name=prospect.lab_name,
                phone=prospect.phone,
                street_address=prospect.address or '',
                city=prospect.city or '',
                state=prospect.state or '',
                zip_code=prospect.zip_code or '',
            )

            # Link the user to the prospect
            prospect.lab_user = lab_user
            prospect.save()

            # Send email with credentials if requested
            email_sent = False
            if send_email and email:
                try:
                    # Build the login URL
                    if hasattr(settings, 'SITE_URL'):
                        login_url = f"{settings.SITE_URL}/accounts/login/"
                    else:
                        login_url = "http://your-domain.com/accounts/login/"

                    # Prepare context for email template
                    context = {
                        'lab_name': prospect.lab_name,
                        'username': username,
                        'password': password,
                        'login_url': login_url,
                        'current_year': datetime.now().year,
                    }

                    # Render email templates
                    html_message = render_to_string('mgmt/email/new_lab_credentials.html', context)
                    plain_message = render_to_string('mgmt/email/new_lab_credentials.txt', context)

                    # Send email
                    send_mail(
                        subject='Welcome to AMS Fusion - Your Lab Account is Ready!',
                        message=plain_message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        html_message=html_message,
                        fail_silently=False,
                    )
                    email_sent = True
                except Exception as e:
                    messages.warning(request, f'Account created but failed to send email: {str(e)}')

            # Show success message with credentials
            if email_sent:
                messages.success(
                    request,
                    f'Lab account created successfully for "{prospect.lab_name}"! '
                    f'Credentials have been emailed to {email}.'
                )
            else:
                messages.success(
                    request,
                    f'Lab account created successfully for "{prospect.lab_name}"! '
                    f'Username: {username} | Password: {password}'
                )

            return redirect('prospects:prospect_detail', pk=pk)
    else:
        # Pre-populate form with prospect data
        # Generate default username from lab name
        base_username = ''.join(prospect.lab_name.lower().split())[:20]
        username = base_username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        form = CreateLabAccountForm(initial={
            'username': username,
            'email': prospect.email,
            'send_email': bool(prospect.email),
        })

    context = {
        'form': form,
        'prospect': prospect,
        'title': f'Create Account for {prospect.lab_name}'
    }
    return render(request, 'prospects/create_lab_account.html', context)


@login_required
def send_fusion_email(request, pk):
    """Send 'What is Fusion' email to a prospect"""
    if request.user.is_caller_user():
        return redirect('prospects:caller_dashboard')
    prospect = get_object_or_404(Prospect, pk=pk)

    if request.method != 'POST':
        return redirect('prospects:prospect_edit', pk=pk)

    if not prospect.email:
        messages.error(request, f'No email address on file for "{prospect.lab_name}".')
        return redirect('prospects:prospect_edit', pk=pk)

    try:
        send_mail(
            subject='What is Fusion',
            message=(
                f'Thank you {prospect.person_name} for your interest in Fusion.\n\n'
                'Below is a web link that has a Video and Text description of Fusion.\n'
                'I look forward to a follow up phone call with you soon.\n\n'
                'https://fusiondentaldesigncenters.com/fusion-a-rescue-response-for-the-dental-lab-industry/\n\n'
                'You can always reach me on my personal cell phone at 708 502-3411\n\n'
                'To learn more about what AmericaSmiles can do to help you succeed in the dental lab industry, visit:\n'
                'https://americasmiles.net/\n\n\n'
                'Kind Regards,\n'
                'Keith Crittenden\n'
                'AmericaSmiles Network'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[prospect.email],
            fail_silently=False,
        )
        messages.success(request, f'"What is Fusion" email sent to {prospect.email}.')
    except Exception as e:
        messages.error(request, f'Failed to send email: {str(e)}')

    return redirect('prospects:prospect_edit', pk=pk)


@login_required
@caller_required
def caller_dashboard(request):
    """Caller's main dashboard showing prospects from mailer campaigns"""
    status_filter = request.GET.get('status', '')
    mailer_filter = request.GET.get('mailer', '')

    # Caller only sees mailed/callback/sent_to_keith/keith_closed statuses
    caller_statuses = ['mailed', 'callback', 'sent_to_keith', 'keith_closed', 'not_interested', 'left_voicemail']
    prospects = Prospect.objects.filter(status__in=caller_statuses)

    if status_filter and status_filter in caller_statuses:
        prospects = prospects.filter(status=status_filter)
    if mailer_filter:
        prospects = prospects.filter(mailer_id=mailer_filter)

    status_counts = {
        'mailed': Prospect.objects.filter(status='mailed').count(),
        'callback': Prospect.objects.filter(status='callback').count(),
        'sent_to_keith': Prospect.objects.filter(status='sent_to_keith').count(),
        'keith_closed': Prospect.objects.filter(status='keith_closed').count(),
        'not_interested': Prospect.objects.filter(status='not_interested').count(),
        'left_voicemail': Prospect.objects.filter(status='left_voicemail').count(),
    }
    status_counts['total'] = sum(status_counts.values())

    mailers = Mailer.objects.all()

    context = {
        'prospects': prospects,
        'status_filter': status_filter,
        'mailer_filter': mailer_filter,
        'status_counts': status_counts,
        'mailers': mailers,
        'title': 'Caller Dashboard',
    }
    return render(request, 'prospects/caller_dashboard.html', context)


@login_required
@caller_required
def caller_detail(request, pk):
    """Read-only prospect detail for callers"""
    prospect = get_object_or_404(Prospect, pk=pk)
    notes = prospect.notes.all()
    status_filter = request.GET.get('status', '')
    mailer_filter = request.GET.get('mailer', '')

    context = {
        'prospect': prospect,
        'notes': notes,
        'status_filter': status_filter,
        'mailer_filter': mailer_filter,
        'title': f'Prospect: {prospect.lab_name}',
    }
    return render(request, 'prospects/caller_detail.html', context)


@login_required
@caller_required
def caller_edit(request, pk):
    """Caller edit view with 3 action buttons: Call Back, Sent to Keith, Not Interested"""
    prospect = get_object_or_404(Prospect, pk=pk)
    notes = prospect.notes.all()
    status_filter = request.GET.get('status', '')
    mailer_filter = request.GET.get('mailer', '')

    # Build redirect URL with preserved filters
    redirect_url = 'prospects:caller_dashboard'
    filter_params = {}
    if status_filter:
        filter_params['status'] = status_filter
    if mailer_filter:
        filter_params['mailer'] = mailer_filter

    callback_form = CallerCallbackForm()
    sent_to_keith_form = CallerSentToKeithForm()
    not_interested_form = CallerNotInterestedForm()
    left_voicemail_form = CallerLeftVoicemailForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'callback':
            callback_form = CallerCallbackForm(request.POST)
            if callback_form.is_valid():
                prospect.status = 'callback'
                prospect.next_contact_date = callback_form.cleaned_data['callback_date']
                prospect.next_contact_time = callback_form.cleaned_data.get('callback_time')
                prospect.save()
                note_text = callback_form.cleaned_data.get('note')
                if note_text:
                    ProspectNote.objects.create(prospect=prospect, note_text=note_text, created_by=request.user)
                callback_time = callback_form.cleaned_data.get('callback_time')
                time_str = f" at {callback_time.strftime('%I:%M %p')}" if callback_time else ""
                messages.success(request, f'"{prospect.lab_name}" set to Call Back on {prospect.next_contact_date.strftime("%m/%d/%Y")}{time_str}.')
                dashboard_url = reverse('prospects:caller_dashboard')
                if filter_params:
                    dashboard_url += '?' + urlencode(filter_params)
                return redirect(dashboard_url)

        elif action == 'sent_to_keith':
            sent_to_keith_form = CallerSentToKeithForm(request.POST)
            if sent_to_keith_form.is_valid():
                prospect.status = 'sent_to_keith'
                prospect.save()
                LeadReferral.objects.create(
                    prospect=prospect,
                    referred_by=request.user,
                    contact_person=sent_to_keith_form.cleaned_data['contact_person'],
                    appointment_date=sent_to_keith_form.cleaned_data['appointment_date'],
                    appointment_time=sent_to_keith_form.cleaned_data['appointment_time'],
                    notes=sent_to_keith_form.cleaned_data.get('note', ''),
                )
                note_text = sent_to_keith_form.cleaned_data.get('note')
                if note_text:
                    ProspectNote.objects.create(prospect=prospect, note_text=note_text, created_by=request.user)
                ProspectNote.objects.create(
                    prospect=prospect,
                    created_by=request.user,
                    note_text=f"Sent to Keith - Contact: {sent_to_keith_form.cleaned_data['contact_person']}, "
                              f"Appt: {sent_to_keith_form.cleaned_data['appointment_date'].strftime('%m/%d/%Y')} "
                              f"at {sent_to_keith_form.cleaned_data['appointment_time'].strftime('%I:%M %p')}"
                )
                messages.success(request, f'"{prospect.lab_name}" sent to Keith.')
                dashboard_url = reverse('prospects:caller_dashboard')
                if filter_params:
                    dashboard_url += '?' + urlencode(filter_params)
                return redirect(dashboard_url)

        elif action == 'left_voicemail':
            left_voicemail_form = CallerLeftVoicemailForm(request.POST)
            if left_voicemail_form.is_valid():
                prospect.status = 'left_voicemail'
                prospect.save()
                from django.utils import timezone
                today = timezone.now().strftime('%m/%d/%Y')
                ProspectNote.objects.create(
                    prospect=prospect,
                    created_by=request.user,
                    note_text=f"Left voicemail on {today}"
                )
                note_text = left_voicemail_form.cleaned_data.get('note')
                if note_text:
                    ProspectNote.objects.create(prospect=prospect, note_text=note_text, created_by=request.user)
                messages.success(request, f'"{prospect.lab_name}" marked as Left Voicemail.')
                dashboard_url = reverse('prospects:caller_dashboard')
                if filter_params:
                    dashboard_url += '?' + urlencode(filter_params)
                return redirect(dashboard_url)

        elif action == 'not_interested':
            not_interested_form = CallerNotInterestedForm(request.POST)
            if not_interested_form.is_valid():
                prospect.status = 'not_interested'
                prospect.save()
                note_text = not_interested_form.cleaned_data.get('note')
                if note_text:
                    ProspectNote.objects.create(prospect=prospect, note_text=note_text, created_by=request.user)
                messages.success(request, f'"{prospect.lab_name}" marked as Not Interested.')
                dashboard_url = reverse('prospects:caller_dashboard')
                if filter_params:
                    dashboard_url += '?' + urlencode(filter_params)
                return redirect(dashboard_url)

    referrals = prospect.lead_referrals.all()

    context = {
        'prospect': prospect,
        'notes': notes,
        'referrals': referrals,
        'callback_form': callback_form,
        'sent_to_keith_form': sent_to_keith_form,
        'not_interested_form': not_interested_form,
        'left_voicemail_form': left_voicemail_form,
        'status_filter': status_filter,
        'mailer_filter': mailer_filter,
        'title': f'Edit: {prospect.lab_name}',
    }
    return render(request, 'prospects/caller_edit.html', context)


@login_required
@caller_required
def caller_edit_referral(request, pk):
    """Edit an existing LeadReferral"""
    referral = get_object_or_404(LeadReferral, pk=pk)
    prospect = referral.prospect
    status_filter = request.GET.get('status', '')
    mailer_filter = request.GET.get('mailer', '')

    if request.method == 'POST':
        form = CallerEditReferralForm(request.POST, instance=referral)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated.')
            edit_url = reverse('prospects:caller_edit', args=[prospect.pk])
            params = {}
            if status_filter:
                params['status'] = status_filter
            if mailer_filter:
                params['mailer'] = mailer_filter
            if params:
                edit_url += '?' + urlencode(params)
            return redirect(edit_url)
    else:
        form = CallerEditReferralForm(instance=referral)

    filter_params_str = ''
    if status_filter or mailer_filter:
        params = {}
        if status_filter:
            params['status'] = status_filter
        if mailer_filter:
            params['mailer'] = mailer_filter
        filter_params_str = '?' + urlencode(params)

    context = {
        'form': form,
        'referral': referral,
        'prospect': prospect,
        'status_filter': status_filter,
        'mailer_filter': mailer_filter,
        'filter_params_str': filter_params_str,
        'title': f'Edit Appointment: {prospect.lab_name}',
    }
    return render(request, 'prospects/caller_edit_referral.html', context)


@login_required
@caller_required
def caller_delete_referral(request, pk):
    """Delete a LeadReferral (POST only)"""
    referral = get_object_or_404(LeadReferral, pk=pk)
    prospect = referral.prospect
    if request.method == 'POST':
        referral.delete()
        messages.success(request, 'Appointment deleted.')
    edit_url = reverse('prospects:caller_edit', args=[prospect.pk])
    status_filter = request.GET.get('status', '') or request.POST.get('status_filter', '')
    mailer_filter = request.GET.get('mailer', '') or request.POST.get('mailer_filter', '')
    params = {}
    if status_filter:
        params['status'] = status_filter
    if mailer_filter:
        params['mailer'] = mailer_filter
    if params:
        edit_url += '?' + urlencode(params)
    return redirect(edit_url)


@login_required
@caller_required
def caller_edit_note(request, pk):
    """Edit an existing ProspectNote"""
    note = get_object_or_404(ProspectNote, pk=pk)
    prospect = note.prospect
    status_filter = request.GET.get('status', '')
    mailer_filter = request.GET.get('mailer', '')

    if request.method == 'POST':
        form = CallerEditNoteForm(request.POST, instance=note)
        if form.is_valid():
            form.save()
            messages.success(request, 'Note updated.')
            edit_url = reverse('prospects:caller_edit', args=[prospect.pk])
            params = {}
            if status_filter:
                params['status'] = status_filter
            if mailer_filter:
                params['mailer'] = mailer_filter
            if params:
                edit_url += '?' + urlencode(params)
            return redirect(edit_url)
    else:
        form = CallerEditNoteForm(instance=note)

    filter_params_str = ''
    if status_filter or mailer_filter:
        params = {}
        if status_filter:
            params['status'] = status_filter
        if mailer_filter:
            params['mailer'] = mailer_filter
        filter_params_str = '?' + urlencode(params)

    context = {
        'form': form,
        'note': note,
        'prospect': prospect,
        'status_filter': status_filter,
        'mailer_filter': mailer_filter,
        'filter_params_str': filter_params_str,
        'title': f'Edit Note: {prospect.lab_name}',
    }
    return render(request, 'prospects/caller_edit_note.html', context)


@login_required
@caller_required
def caller_delete_note(request, pk):
    """Delete a ProspectNote (POST only)"""
    note = get_object_or_404(ProspectNote, pk=pk)
    prospect = note.prospect
    if request.method == 'POST':
        note.delete()
        messages.success(request, 'Note deleted.')
    edit_url = reverse('prospects:caller_edit', args=[prospect.pk])
    status_filter = request.GET.get('status', '') or request.POST.get('status_filter', '')
    mailer_filter = request.GET.get('mailer', '') or request.POST.get('mailer_filter', '')
    params = {}
    if status_filter:
        params['status'] = status_filter
    if mailer_filter:
        params['mailer'] = mailer_filter
    if params:
        edit_url += '?' + urlencode(params)
    return redirect(edit_url)


@login_required
def lead_referrals(request):
    """Keith's view of leads sent by callers"""
    referrals = LeadReferral.objects.select_related('prospect', 'referred_by').all()

    context = {
        'referrals': referrals,
        'title': 'Leads from AMS Caller',
    }
    return render(request, 'prospects/lead_referrals.html', context)


@login_required
def caller_activity(request):
    """Admin view to monitor caller activity by date"""
    if request.user.is_caller_user():
        return redirect('prospects:caller_dashboard')

    selected_date = request.GET.get('date', '')
    if selected_date:
        try:
            selected_date = date.fromisoformat(selected_date)
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    # Get all caller users
    callers = CustomUser.objects.filter(user_type='caller')

    # Build timezone-aware date range for filtering
    from django.utils import timezone as tz
    import datetime as dt
    day_start = tz.make_aware(dt.datetime.combine(selected_date, dt.time.min))
    day_end = tz.make_aware(dt.datetime.combine(selected_date, dt.time.max))

    caller_stats = []
    for caller in callers:
        # Notes created by this caller on the selected date
        notes = ProspectNote.objects.filter(
            created_by=caller,
            created_at__gte=day_start,
            created_at__lte=day_end
        ).select_related('prospect').order_by('-created_at')

        # Unique prospects touched
        prospects_touched = notes.values('prospect').distinct().count()

        caller_stats.append({
            'caller': caller,
            'note_count': notes.count(),
            'prospects_touched': prospects_touched,
            'notes': notes,
        })

    context = {
        'selected_date': selected_date,
        'caller_stats': caller_stats,
        'title': 'Caller Activity Report',
    }
    return render(request, 'prospects/caller_activity.html', context)
