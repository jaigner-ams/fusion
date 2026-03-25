from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_POST
from onevoice.decorators import csr_required
from onevoice.models import (
    OVClient, OVDentist, OVDentistStatusHistory, OVCallRecord,
    OVAppointment, OVCallSession, OVClientAvailability, OVNotification,
)
from onevoice.notifications import send_ov_notification


# ── CSR Dashboard ──

@csr_required
def csr_dashboard(request):
    today = timezone.now().date()
    clients = OVClient.objects.filter(status='active')

    todays_sessions = OVCallSession.objects.filter(
        scheduled_date=today,
        status__in=['scheduled', 'in_progress'],
    ).select_related('client', 'csr')

    week_end = today + timedelta(days=(6 - today.weekday()))
    this_week_sessions = OVCallSession.objects.filter(
        scheduled_date__gte=today,
        scheduled_date__lte=week_end,
    ).select_related('client', 'csr')

    next_week_start = week_end + timedelta(days=1)
    next_week_end = next_week_start + timedelta(days=6)
    next_week_sessions = OVCallSession.objects.filter(
        scheduled_date__gte=next_week_start,
        scheduled_date__lte=next_week_end,
    ).select_related('client', 'csr')

    # Build calendar data: current week + next week as day-by-day
    from collections import defaultdict
    calendar_days = []
    current_week_start = today - timedelta(days=today.weekday())  # Monday
    all_sessions = OVCallSession.objects.filter(
        scheduled_date__gte=current_week_start,
        scheduled_date__lte=next_week_end,
    ).select_related('client', 'csr')

    sessions_by_date = defaultdict(list)
    for s in all_sessions:
        sessions_by_date[s.scheduled_date].append(s)

    for i in range(14):  # 2 weeks
        day = current_week_start + timedelta(days=i)
        calendar_days.append({
            'date': day,
            'is_today': day == today,
            'is_past': day < today,
            'sessions': sessions_by_date.get(day, []),
            'is_weekend': day.weekday() >= 5,
        })

    context = {
        'clients': clients,
        'todays_sessions': todays_sessions,
        'this_week_sessions': this_week_sessions,
        'next_week_sessions': next_week_sessions,
        'today': today,
        'calendar_days': calendar_days,
    }
    return render(request, 'onevoice/csr/dashboard.html', context)


# ── Client Summary Panel ──

@csr_required
def csr_client_panel(request, client_pk):
    client = get_object_or_404(OVClient, pk=client_pk)
    dentists = client.dentists.exclude(status='removed')
    status_counts = dentists.values('status').annotate(count=Count('id'))
    status_map = {s['status']: s['count'] for s in status_counts}

    email_count = dentists.filter(status='email_captured').count()
    appt_count = client.appointments.filter(status='scheduled').count()

    latest_session = client.call_sessions.first()
    next_mailing = client.mailing_schedule.filter(
        completed=False, scheduled_date__gte=timezone.now().date()
    ).first()

    context = {
        'client': client,
        'dentist_count': dentists.count(),
        'status_map': status_map,
        'email_count': email_count,
        'appt_count': appt_count,
        'latest_session': latest_session,
        'next_mailing': next_mailing,
    }
    return render(request, 'onevoice/csr/client_panel.html', context)


# ── Color-coded Dentist List ──

@csr_required
def csr_dentist_list(request, client_pk):
    client = get_object_or_404(OVClient, pk=client_pk)
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
    return render(request, 'onevoice/csr/dentist_list.html', context)


# ── Individual Dentist Record ──

@csr_required
def csr_dentist_record(request, pk):
    dentist = get_object_or_404(OVDentist, pk=pk)
    from onevoice.forms import OVCallRecordForm

    # Record locking check
    locked_by_other = False
    if dentist.is_locked() and dentist.locked_by != request.user:
        locked_by_other = True
    elif not dentist.is_locked() or dentist.locked_by == request.user:
        dentist.acquire_lock(request.user)

    if request.method == 'POST' and not locked_by_other:
        form = OVCallRecordForm(request.POST)
        if form.is_valid():
            call = form.save(commit=False)
            call.dentist = dentist
            call.csr = request.user

            # Find active session for this client
            active_session = OVCallSession.objects.filter(
                client=dentist.client,
                status='in_progress',
            ).first()
            call.session = active_session
            call.save()

            # Update dentist status based on outcome
            old_status = dentist.status
            new_status = old_status

            if call.outcome == 'spoke_appointment':
                new_status = 'appointment'
            elif call.outcome == 'spoke_email_captured':
                new_status = 'email_captured'
                if call.email_captured:
                    dentist.email = call.email_captured
            elif call.outcome in ('no_answer', 'voicemail'):
                new_status = 'no_answer'
            elif call.outcome == 'confirmed_active':
                # Confirmed active — keep current status or mark as called
                if old_status == 'never_called':
                    new_status = 'called_no_email' if not dentist.email else 'email_captured'
            elif call.outcome in ('spoke_not_interested', 'spoke_callback', 'other'):
                if not dentist.email:
                    new_status = 'called_no_email'
            elif call.outcome in ('do_not_contact', 'wrong_number', 'disconnected', 'out_of_business'):
                new_status = 'do_not_contact'

            if new_status != old_status:
                OVDentistStatusHistory.objects.create(
                    dentist=dentist,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user,
                    notes=f'Call outcome: {call.get_outcome_display()}',
                )
                dentist.status = new_status

            # Handle callback
            if call.outcome == 'spoke_callback':
                dentist.callback_flag = True
                dentist.callback_date = call.callback_date
                dentist.callback_time = call.callback_time
            else:
                dentist.callback_flag = False

            dentist.notes = call.notes if call.notes else dentist.notes
            dentist.release_lock()
            dentist.save()

            messages.success(request, f'Call logged for {dentist.name}: {call.get_outcome_display()}')

            # If appointment booked, redirect to booking form
            if call.outcome == 'spoke_appointment':
                return redirect('onevoice:csr_book_appointment', pk=dentist.pk)

            return redirect('onevoice:csr_dentist_list', client_pk=dentist.client_id)
    else:
        form = OVCallRecordForm()

    call_history = dentist.call_records.select_related('csr')[:10]
    status_history = dentist.status_history.all()[:10]

    context = {
        'dentist': dentist,
        'client': dentist.client,
        'form': form,
        'locked_by_other': locked_by_other,
        'call_history': call_history,
        'status_history': status_history,
    }
    return render(request, 'onevoice/csr/dentist_record.html', context)


# ── Book Appointment ──

@csr_required
def csr_book_appointment(request, pk):
    dentist = get_object_or_404(OVDentist, pk=pk)
    client = dentist.client
    from onevoice.forms import OVAppointmentForm

    if request.method == 'POST':
        form = OVAppointmentForm(request.POST)
        if form.is_valid():
            appt_date = form.cleaned_data['appointment_date']
            appt_time = form.cleaned_data['appointment_time']

            # Check double-booking
            if OVAppointment.objects.filter(
                client=client, appointment_date=appt_date, appointment_time=appt_time,
                status='scheduled',
            ).exists():
                messages.error(request, 'This time slot is already booked for this client.')
                return render(request, 'onevoice/csr/book_appointment.html', {
                    'dentist': dentist, 'client': client, 'form': form,
                })

            # Check client availability
            day_of_week = appt_date.weekday()
            available = OVClientAvailability.objects.filter(
                client=client, is_active=True,
            ).filter(
                Q(availability_type='recurring', day_of_week=day_of_week) |
                Q(availability_type='specific', specific_date=appt_date)
            ).filter(
                start_time__lte=appt_time, end_time__gte=appt_time,
            ).exists()

            # Availability is optional - warn but don't block
            if not available and OVClientAvailability.objects.filter(client=client, is_active=True).exists():
                messages.warning(request, 'Note: This time falls outside the client\'s stated availability.')

            # Travel time flagging: check same-day appointments
            same_day_appts = OVAppointment.objects.filter(
                client=client, appointment_date=appt_date, status='scheduled',
            ).select_related('dentist')
            if same_day_appts.exists() and dentist.zip_code:
                from mgmt.models import ZipCode
                for existing in same_day_appts:
                    if existing.dentist.zip_code and existing.dentist.zip_code != dentist.zip_code:
                        coords1 = ZipCode.get_coordinates(dentist.zip_code)
                        coords2 = ZipCode.get_coordinates(existing.dentist.zip_code)
                        if coords1 and coords2:
                            dist = ZipCode.haversine_distance(coords1[0], coords1[1], coords2[0], coords2[1])
                            if dist > 30:
                                time_diff = abs(
                                    (appt_time.hour * 60 + appt_time.minute) -
                                    (existing.appointment_time.hour * 60 + existing.appointment_time.minute)
                                )
                                if time_diff < 60:
                                    messages.warning(
                                        request,
                                        f'Travel warning: {dist:.0f} miles between this appointment and '
                                        f'{existing.dentist.name} at {existing.appointment_time.strftime("%I:%M %p")} '
                                        f'with only {time_diff} min gap.'
                                    )

            appt = form.save(commit=False)
            appt.client = client
            appt.dentist = dentist
            appt.booked_by = request.user
            appt.save()

            # Notify client
            if client.user:
                send_ov_notification(
                    'appointment_booked', client.user, client=client,
                    title=f'Appointment Booked: {dentist.name}',
                    message=f'Appointment with {dentist.name} ({dentist.practice_name}) on {appt_date.strftime("%b %d, %Y")} at {appt_time.strftime("%I:%M %p")}.',
                )

            # Mode 2: auto-pause active session
            if client.call_session_mode == 2:
                active_session = OVCallSession.objects.filter(
                    client=client, status='in_progress',
                ).first()
                if active_session:
                    active_session.status = 'completed'
                    active_session.completed_at = timezone.now()
                    active_session.notes = (active_session.notes or '') + f'\nAuto-paused: Mode 2 appointment booked for {appt_date}.'
                    active_session.save()
                messages.info(request, f'Mode 2: Session paused. Calls resume after the {appt_date.strftime("%b %d")} appointment passes.')

            messages.success(request, f'Appointment booked with {dentist.name} on {appt_date.strftime("%b %d, %Y")}.')
            return redirect('onevoice:csr_client_panel', client_pk=client.pk)
    else:
        form = OVAppointmentForm()

    # Get client availability for display
    availability = OVClientAvailability.objects.filter(client=client, is_active=True)

    context = {
        'dentist': dentist,
        'client': client,
        'form': form,
        'availability': availability,
    }
    return render(request, 'onevoice/csr/book_appointment.html', context)


# ── Session Controls ──

@csr_required
def csr_session_begin(request, pk):
    session = get_object_or_404(OVCallSession, pk=pk)
    if request.method == 'POST':
        session.status = 'in_progress'
        session.started_at = timezone.now()
        session.csr = request.user
        session.save()

        # Notify client
        if session.client.user:
            send_ov_notification(
                'session_started', session.client.user, client=session.client,
                title='Your Call Session Has Begun',
                message=f'Your CSR has started calling dentists on your behalf.',
            )

        messages.success(request, f'Call session started for {session.client.lab_name}.')
    return redirect('onevoice:csr_client_panel', client_pk=session.client_id)


@csr_required
def csr_session_done(request, pk):
    session = get_object_or_404(OVCallSession, pk=pk)
    if request.method == 'POST':
        session.status = 'completed'
        session.completed_at = timezone.now()
        session.save()

        # Notify admins
        from mgmt.models import CustomUser
        admins = CustomUser.objects.filter(user_type__in=['ov_admin', 'superadmin'])
        for admin in admins:
            send_ov_notification(
                'session_done', admin, client=session.client,
                title=f'Call Session Completed: {session.client.lab_name}',
                message=f'CSR {request.user.first_name or request.user.username} has completed the call session.',
            )

        messages.success(request, f'Call session completed for {session.client.lab_name}.')
    return redirect('onevoice:csr_dashboard')


# ── AJAX: Record Locking ──

@csr_required
def dentist_lock_api(request, pk):
    """AJAX endpoint to refresh/acquire lock."""
    dentist = get_object_or_404(OVDentist, pk=pk)
    if request.method == 'POST':
        success = dentist.acquire_lock(request.user)
        return JsonResponse({'locked': success})
    return JsonResponse({'error': 'POST required'}, status=405)


@csr_required
def dentist_unlock_api(request, pk):
    """AJAX endpoint to release lock."""
    dentist = get_object_or_404(OVDentist, pk=pk)
    if request.method == 'POST':
        if dentist.locked_by == request.user:
            dentist.release_lock()
        return JsonResponse({'unlocked': True})
    return JsonResponse({'error': 'POST required'}, status=405)
