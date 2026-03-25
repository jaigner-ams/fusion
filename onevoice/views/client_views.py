from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from onevoice.decorators import ov_client_required
from onevoice.models import (
    OVClient, OVDentist, OVAppointment, OVAgreement, OVNotification,
    OVClientAvailability, OVPostcardDesign, OVPostcardComment,
    OVMailingSchedule, OVCallSession,
)
from onevoice.notifications import send_ov_notification


def _get_client(request):
    """Get the OVClient for the logged-in ov_client user."""
    try:
        return request.user.ov_client_profile
    except OVClient.DoesNotExist:
        return None


# ── Dashboard ──

@ov_client_required
def client_dashboard(request):
    client = _get_client(request)
    if not client:
        messages.error(request, 'No client profile found for your account.')
        return render(request, 'onevoice/client/dashboard.html', {})

    total_dentists = client.get_active_dentist_count()
    status_counts = {}
    for d in client.dentists.exclude(status='removed').values_list('status', flat=True):
        status_counts[d] = status_counts.get(d, 0) + 1

    email_count = client.dentists.filter(status='email_captured').count()
    upcoming = OVAppointment.objects.filter(
        client=client, appointment_date__gte=timezone.now().date(), status='scheduled',
    ).select_related('dentist')[:5]

    unread_count = OVNotification.objects.filter(recipient=request.user, read=False).count()

    # Last activity: most recent call record for this client's dentists
    from onevoice.models import OVCallRecord
    last_call = OVCallRecord.objects.filter(
        dentist__client=client,
    ).order_by('-called_at').first()
    last_activity = last_call.called_at if last_call else client.updated_at

    # Postcard mailing status
    next_mailing = client.mailing_schedule.filter(
        completed=False, scheduled_date__gte=timezone.now().date(),
    ).first()
    last_mailing = client.mailing_schedule.filter(completed=True).order_by('-scheduled_date').first()

    # Postcard inventory
    from onevoice.models import OVPostcardInventory
    inventory = OVPostcardInventory.objects.filter(client=client)
    total_on_hand = sum(inv.quantity_on_hand for inv in inventory)
    reorder_needed = any(inv.is_below_threshold() for inv in inventory)

    context = {
        'client': client,
        'total_dentists': total_dentists,
        'status_counts': status_counts,
        'email_count': email_count,
        'upcoming_appointments': upcoming,
        'unread_count': unread_count,
        'last_activity': last_activity,
        'next_mailing': next_mailing,
        'last_mailing': last_mailing,
        'total_on_hand': total_on_hand,
        'reorder_needed': reorder_needed,
    }
    return render(request, 'onevoice/client/dashboard.html', context)


# ── Prospect List (read-only) ──

@ov_client_required
def client_prospect_list(request):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    status_filter = request.GET.get('status', '')
    dentists = client.dentists.exclude(status='removed')
    if status_filter:
        dentists = dentists.filter(status=status_filter)

    context = {
        'client': client,
        'dentists': dentists,
        'status_filter': status_filter,
        'status_choices': OVDentist.STATUS_CHOICES,
    }
    return render(request, 'onevoice/client/prospect_list.html', context)


# ── Correction Request ──

@ov_client_required
def client_correction_request(request, pk):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    dentist = get_object_or_404(OVDentist, pk=pk, client=client)

    if request.method == 'POST':
        from onevoice.forms import OVDentistCorrectionForm
        form = OVDentistCorrectionForm(request.POST)
        if form.is_valid():
            dentist.correction_requested = True
            dentist.correction_notes = form.cleaned_data['correction_notes']
            dentist.save(update_fields=['correction_requested', 'correction_notes'])

            # Notify admins
            from mgmt.models import CustomUser
            for admin in CustomUser.objects.filter(user_type__in=['ov_admin', 'superadmin']):
                send_ov_notification(
                    'correction_request', admin, client=client,
                    title=f'Correction Request: {dentist.name}',
                    message=f'{client.lab_name} requests correction for {dentist.name}: {dentist.correction_notes}',
                )

            messages.success(request, f'Correction request submitted for {dentist.name}.')
            return redirect('onevoice:client_prospect_list')
    else:
        from onevoice.forms import OVDentistCorrectionForm
        form = OVDentistCorrectionForm()

    return render(request, 'onevoice/client/correction_form.html', {
        'dentist': dentist, 'client': client, 'form': form,
    })


# ── Removal Request ──

@ov_client_required
def client_removal_request(request, pk):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    dentist = get_object_or_404(OVDentist, pk=pk, client=client)
    if request.method == 'POST':
        dentist.removal_flagged = True
        dentist.save(update_fields=['removal_flagged'])

        from mgmt.models import CustomUser
        for admin in CustomUser.objects.filter(user_type__in=['ov_admin', 'superadmin']):
            send_ov_notification(
                'removal_request', admin, client=client,
                title=f'Removal Request: {dentist.name}',
                message=f'{client.lab_name} flagged {dentist.name} for removal.',
            )

        messages.success(request, f'{dentist.name} flagged for removal.')
    return redirect('onevoice:client_prospect_list')


# ── Upcoming Appointments ──

@ov_client_required
def client_appointments(request):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    appointments = OVAppointment.objects.filter(
        client=client, appointment_date__gte=timezone.now().date(), status='scheduled',
    ).select_related('dentist').order_by('appointment_date', 'appointment_time')

    return render(request, 'onevoice/client/appointments.html', {
        'client': client, 'appointments': appointments,
    })


# ── Previous Appointments ──

@ov_client_required
def client_previous_appointments(request):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    appointments = OVAppointment.objects.filter(
        client=client,
    ).filter(
        appointment_date__lt=timezone.now().date(),
    ).select_related('dentist').order_by('-appointment_date')

    return render(request, 'onevoice/client/previous_appointments.html', {
        'client': client, 'appointments': appointments,
    })


# ── Follow-up ──

@ov_client_required
def client_followup(request, pk):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    appointment = get_object_or_404(OVAppointment, pk=pk, client=client)
    from onevoice.forms import OVAppointmentFollowupForm

    if request.method == 'POST':
        form = OVAppointmentFollowupForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Follow-up updated.')
            return redirect('onevoice:client_previous_appointments')
    else:
        form = OVAppointmentFollowupForm(instance=appointment)

    return render(request, 'onevoice/client/followup_form.html', {
        'client': client, 'appointment': appointment, 'form': form,
    })


# ── Availability ──

@ov_client_required
def client_availability(request):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    from onevoice.forms import OVClientAvailabilityForm

    if request.method == 'POST':
        if 'delete_id' in request.POST:
            OVClientAvailability.objects.filter(
                pk=request.POST['delete_id'], client=client,
            ).delete()
            messages.success(request, 'Availability slot removed.')
            return redirect('onevoice:client_availability')

        form = OVClientAvailabilityForm(request.POST)
        if form.is_valid():
            avail = form.save(commit=False)
            avail.client = client
            avail.save()
            messages.success(request, 'Availability added.')
            return redirect('onevoice:client_availability')
    else:
        form = OVClientAvailabilityForm()

    availability = OVClientAvailability.objects.filter(client=client, is_active=True)

    return render(request, 'onevoice/client/availability.html', {
        'client': client, 'form': form, 'availability': availability,
    })


# ── Postcards ──

@ov_client_required
def client_postcard_view(request):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    designs = OVPostcardDesign.objects.filter(client=client)
    master_templates = OVPostcardDesign.objects.filter(is_master_template=True)

    return render(request, 'onevoice/client/postcards.html', {
        'client': client, 'designs': designs, 'master_templates': master_templates,
    })


@ov_client_required
def client_postcard_approve(request, pk):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    design = get_object_or_404(OVPostcardDesign, pk=pk, client=client)
    if request.method == 'POST' and not design.locked:
        design.approved_by_client = True
        design.approved_at = timezone.now()
        design.status = 'locked'
        design.locked = True
        design.locked_at = timezone.now()
        design.save()
        messages.success(request, f'Design "{design.name}" approved and locked.')
    return redirect('onevoice:client_postcard_view')


@ov_client_required
def client_postcard_comment(request, pk):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    design = get_object_or_404(OVPostcardDesign, pk=pk, client=client)
    if request.method == 'POST':
        from onevoice.forms import OVPostcardCommentForm
        form = OVPostcardCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.design = design
            comment.user = request.user
            comment.save()
            messages.success(request, 'Comment added.')
    return redirect('onevoice:client_postcard_view')


# ── Schedule ──

@ov_client_required
def client_schedule_view(request):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    mailings = OVMailingSchedule.objects.filter(client=client)
    sessions = OVCallSession.objects.filter(client=client)

    return render(request, 'onevoice/client/schedule.html', {
        'client': client, 'mailings': mailings, 'sessions': sessions,
    })


# ── Sign Agreement ──

@ov_client_required
def client_sign_agreement(request, pk):
    client = _get_client(request)
    if not client:
        return redirect('onevoice:client_dashboard')

    agreement = get_object_or_404(OVAgreement, pk=pk, client=client)
    if agreement.signed:
        messages.info(request, 'This agreement has already been signed.')
        return redirect('onevoice:client_dashboard')

    if request.method == 'POST':
        signature_name = request.POST.get('signature_name', '').strip()
        if signature_name:
            agreement.signed = True
            agreement.signature_name = signature_name
            agreement.signature_date = timezone.now()
            agreement.ip_address = request.META.get('REMOTE_ADDR')
            agreement.save()
            messages.success(request, 'Agreement signed successfully.')
            return redirect('onevoice:client_dashboard')
        else:
            messages.error(request, 'Please type your name to sign.')

    return render(request, 'onevoice/client/agreement_sign.html', {
        'client': client, 'agreement': agreement,
    })


# ── Contact AMS ──

@ov_client_required
def client_contact(request):
    client = _get_client(request)
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        body = request.POST.get('message', '').strip()
        if subject and body:
            from django.core.mail import send_mail
            from django.conf import settings
            try:
                send_mail(
                    subject=f'[One Voice] {subject} — {client.lab_name if client else "Unknown"}',
                    message=f'From: {request.user.first_name} {request.user.last_name} ({request.user.email})\n\n{body}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=['info@amsfusion.com'],
                    fail_silently=True,
                )
                messages.success(request, 'Message sent to AMS.')
            except Exception:
                messages.error(request, 'Could not send message. Please call 708-502-3411.')
            return redirect('onevoice:client_contact')

    return render(request, 'onevoice/client/contact.html', {'client': client})
