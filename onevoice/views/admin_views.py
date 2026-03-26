import csv
import io
import random
import string
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.http import JsonResponse
from django.db.models import Count, Q
from mgmt.models import CustomUser
from onevoice.decorators import ov_admin_required
from onevoice.models import (
    OVClient, OVAgreement, OVDentist, OVDentistStatusHistory,
    OVCallSession, OVNotification, OVListImport, OVPostcardDesign,
    OVPostcardInventory, OVMailingSchedule, OVCallRecord, OVAppointment,
    OVBillingSnapshot,
)
from onevoice.notifications import send_ov_notification


def generate_password(length=12):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def generate_username(owner_name, lab_name):
    """Generate a username from owner name or lab name."""
    base = owner_name.lower().replace(' ', '.') if owner_name else lab_name.lower().replace(' ', '')
    base = ''.join(c for c in base if c.isalnum() or c == '.')[:20]
    username = base
    counter = 1
    while CustomUser.objects.filter(username=username).exists():
        username = f'{base}{counter}'
        counter += 1
    return username


# ── Dashboard ──

@ov_admin_required
def admin_dashboard(request):
    clients = OVClient.objects.all()
    active_clients = clients.filter(status='active').count()
    onboarding_clients = clients.filter(status='onboarding').count()
    total_clients = clients.count()

    pending_corrections = OVDentist.objects.filter(correction_requested=True).count()
    removal_requests = OVDentist.objects.filter(removal_flagged=True).count()

    upcoming_sessions = OVCallSession.objects.filter(
        scheduled_date__gte=timezone.now().date(),
        status__in=['scheduled', 'in_progress'],
    ).select_related('client', 'csr')[:5]

    unread_count = OVNotification.objects.filter(
        recipient=request.user, read=False,
    ).count()

    # Auto-sync: create OVClient records for OneVoice prospects that don't have one yet
    from prospects.models import Prospect
    ov_prospects = Prospect.objects.filter(
        ams_history='current_onevoice',
    ).exclude(
        ov_client__isnull=False,
    )
    for prospect in ov_prospects:
        username = prospect.email or generate_username(prospect.person_name, prospect.lab_name)
        password = prospect.zip_code or generate_password()
        if CustomUser.objects.filter(username=username).exists():
            continue
        user = CustomUser.objects.create_user(
            username=username,
            email=prospect.email or '',
            password=password,
            user_type='ov_client',
            first_name=prospect.person_name.split()[0] if prospect.person_name else '',
            last_name=' '.join(prospect.person_name.split()[1:]) if prospect.person_name else '',
        )
        client = OVClient.objects.create(
            prospect=prospect,
            user=user,
            lab_name=prospect.lab_name,
            owner_name=prospect.person_name,
            address=prospect.address or '',
            city=prospect.city or '',
            state=prospect.state or '',
            zip_code=prospect.zip_code or '',
            phone=prospect.phone or '',
            email=prospect.email or '',
            status='active',
        )
        # Send welcome email
        email_context = {
            'client': client,
            'username': username,
            'password': password,
            'site_url': getattr(settings, 'SITE_URL', 'https://amsfusion.com'),
        }
        try:
            html_message = render_to_string('onevoice/emails/welcome.html', email_context)
            send_mail(
                subject='Welcome to One Voice — AmericaSmiles Network',
                message=f'Welcome to One Voice! Your login: {username} / {password}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[prospect.email] if prospect.email else [],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception:
            pass

    # Re-fetch after sync
    clients = OVClient.objects.all()
    total_clients = clients.count()
    active_clients = clients.filter(status='active').count()
    onboarding_clients = clients.filter(status='onboarding').count()

    context = {
        'active_clients': active_clients,
        'onboarding_clients': onboarding_clients,
        'total_clients': total_clients,
        'pending_corrections': pending_corrections,
        'removal_requests': removal_requests,
        'upcoming_sessions': upcoming_sessions,
        'unread_count': unread_count,
        'recent_clients': clients.select_related('user', 'prospect')[:10],
    }
    return render(request, 'onevoice/admin/dashboard.html', context)


# ── Client List ──

@ov_admin_required
def client_list(request):
    status_filter = request.GET.get('status', '')
    clients = OVClient.objects.all().select_related('user', 'prospect')
    if status_filter:
        clients = clients.filter(status=status_filter)

    context = {
        'clients': clients,
        'status_filter': status_filter,
        'status_choices': OVClient.STATUS_CHOICES,
    }
    return render(request, 'onevoice/admin/client_list.html', context)


# ── Client Add (Onboarding) ──

@ov_admin_required
def client_add(request):
    from onevoice.forms import OVClientForm
    if request.method == 'POST':
        form = OVClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)

            # Create user account
            username = client.email or generate_username(client.owner_name, client.lab_name)
            password = client.zip_code or generate_password()
            user = CustomUser.objects.create_user(
                username=username,
                email=client.email,
                password=password,
                user_type='ov_client',
                first_name=client.owner_name.split()[0] if client.owner_name else '',
                last_name=' '.join(client.owner_name.split()[1:]) if client.owner_name else '',
            )
            client.user = user
            client.save()

            # Send welcome email
            email_context = {
                'client': client,
                'username': username,
                'password': password,
                'site_url': getattr(settings, 'SITE_URL', 'https://amsfusion.com'),
            }
            try:
                html_message = render_to_string('onevoice/emails/welcome.html', email_context)
                send_mail(
                    subject='Welcome to One Voice — AmericaSmiles Network',
                    message=f'Welcome to One Voice! Your login: {username} / {password}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[client.email] if client.email else [],
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception:
                pass

            # Create welcome notification
            send_ov_notification(
                'welcome', user, client=client,
                title='Welcome to One Voice',
                message=f'Your One Voice account has been created. Username: {username}',
                send_email=False,  # Already sent above
            )

            messages.success(request, f'Client "{client.lab_name}" onboarded successfully. Credentials: {username} / {password}')
            return redirect('onevoice:client_detail', pk=client.pk)
    else:
        form = OVClientForm()

    return render(request, 'onevoice/admin/client_form.html', {'form': form, 'is_edit': False})


# ── Client Detail ──

@ov_admin_required
def client_detail(request, pk):
    client = get_object_or_404(OVClient, pk=pk)
    dentists = client.dentists.exclude(status='removed')
    sessions = client.call_sessions.all()[:10]
    appointments = client.appointments.filter(status='scheduled').order_by('appointment_date')[:5]
    agreements = client.agreements.all()
    imports = client.list_imports.all()[:5]

    # Status breakdown
    status_counts = dentists.values('status').annotate(count=Count('id'))
    status_map = {s['status']: s['count'] for s in status_counts}

    context = {
        'client': client,
        'dentists': dentists[:20],
        'dentist_count': dentists.count(),
        'status_map': status_map,
        'sessions': sessions,
        'appointments': appointments,
        'agreements': agreements,
        'imports': imports,
        'overage': client.get_overage_count(),
    }
    return render(request, 'onevoice/admin/client_detail.html', context)


# ── Client Edit ──

@ov_admin_required
def client_edit(request, pk):
    client = get_object_or_404(OVClient, pk=pk)
    from onevoice.forms import OVClientEditForm
    if request.method == 'POST':
        form = OVClientEditForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, f'Client "{client.lab_name}" updated.')
            return redirect('onevoice:client_detail', pk=client.pk)
    else:
        form = OVClientEditForm(instance=client)

    return render(request, 'onevoice/admin/client_form.html', {'form': form, 'is_edit': True, 'client': client})


# ── Send Agreement ──

@ov_admin_required
def send_agreement(request, pk):
    client = get_object_or_404(OVClient, pk=pk)
    from onevoice.forms import OVAgreementSendForm

    if request.method == 'POST':
        form = OVAgreementSendForm(request.POST)
        if form.is_valid():
            agreement = form.save(commit=False)
            agreement.client = client
            agreement.sent_by = request.user
            agreement.save()

            # Notify client
            if client.user:
                send_ov_notification(
                    'agreement_sent', client.user, client=client,
                    title='Service Agreement Ready for Review',
                    message='Your One Voice service agreement is ready. Please review and sign in your portal.',
                )

            messages.success(request, 'Agreement sent to client.')
            return redirect('onevoice:client_detail', pk=client.pk)
    else:
        form = OVAgreementSendForm()

    return render(request, 'onevoice/admin/agreement_send.html', {
        'form': form, 'client': client,
    })


# ── CSV Import ──

KEEP_SPECIALTIES = {'general practice', 'gp', 'general dentist', 'general', 'prosthodontist', 'prosthodontists', 'prostho'}
REMOVE_SPECIALTIES = {'endodontist', 'endodontists', 'endo', 'orthodontist', 'orthodontists', 'ortho',
                      'oral surgeon', 'oral surgery', 'oral surgeons', 'oralsurg',
                      'periodontist', 'periodontists', 'perio',
                      'pedodontist', 'pedodontists', 'pediatric dentist', 'pediatric dentistry', 'pediatric', 'pedo'}


def classify_specialty(raw):
    """Classify a raw specialty string into our system."""
    lower = raw.strip().lower()
    if not lower or lower in KEEP_SPECIALTIES:
        return 'gp'
    if 'prostho' in lower:
        return 'prostho'
    if any(s in lower for s in ['endo']):
        return 'endo'
    if any(s in lower for s in ['ortho']):
        return 'ortho'
    if any(s in lower for s in ['oral surg']):
        return 'oralsurg'
    if any(s in lower for s in ['perio']):
        return 'perio'
    if any(s in lower for s in ['pedo', 'pediatric']):
        return 'pedo'
    return 'gp'


def should_keep(specialty_code):
    return specialty_code in ('gp', 'prostho')


@ov_admin_required
def import_dentist_list(request, pk):
    client = get_object_or_404(OVClient, pk=pk)

    if request.method == 'POST' and 'confirm_import' in request.POST:
        # Phase 2: Confirm import from session data
        import json
        preview_data = request.session.get(f'import_preview_{pk}')
        if not preview_data:
            messages.error(request, 'Import session expired. Please upload again.')
            return redirect('onevoice:import_dentist_list', pk=pk)

        rows = json.loads(preview_data)
        list_import = OVListImport.objects.create(
            client=client,
            file_name=request.session.get(f'import_filename_{pk}', 'unknown.csv'),
            total_rows=len(rows),
            imported_count=0,
            filtered_count=0,
            duplicate_count=0,
            imported_by=request.user,
        )

        imported = 0
        filtered = 0
        duplicates = 0
        for row in rows:
            specialty_code = row.get('specialty_code', 'gp')
            if not should_keep(specialty_code):
                filtered += 1
                continue

            # Check for duplicates by name + phone within this client
            name = row.get('name', '').strip()
            phone = row.get('phone', '').strip()
            if name and phone and OVDentist.objects.filter(client=client, name=name, phone=phone).exists():
                duplicates += 1
                continue

            OVDentist.objects.create(
                client=client,
                list_import=list_import,
                name=name,
                practice_name=row.get('practice_name', ''),
                specialty=specialty_code,
                address=row.get('address', ''),
                city=row.get('city', ''),
                state=row.get('state', ''),
                zip_code=row.get('zip_code', ''),
                phone=phone,
                email=row.get('email', ''),
                contact_person=row.get('contact_person', ''),
            )
            imported += 1

        list_import.imported_count = imported
        list_import.filtered_count = filtered
        list_import.duplicate_count = duplicates
        list_import.save()

        # Clean session
        request.session.pop(f'import_preview_{pk}', None)
        request.session.pop(f'import_filename_{pk}', None)

        # Notify client
        if client.user:
            send_ov_notification(
                'list_ready', client.user, client=client,
                title='Your Prospect List is Ready',
                message=f'{imported} dentists have been added to your list.',
            )

        # Check overage
        overage = client.get_overage_count()
        if overage > 0:
            messages.warning(request, f'List size exceeds approved size by {overage}. Overage: ${client.get_overage_amount():.2f}/mo.')

        messages.success(request, f'Imported {imported} dentists. Filtered: {filtered}. Duplicates skipped: {duplicates}.')
        return redirect('onevoice:client_detail', pk=pk)

    elif request.method == 'POST' and 'csv_file' in request.FILES:
        # Phase 1: Upload and preview
        csv_file = request.FILES['csv_file']
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('onevoice:import_dentist_list', pk=pk)

        import json
        decoded = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))

        rows = []
        keep_count = 0
        filter_count = 0
        for raw_row in reader:
            # Normalize field names (case-insensitive)
            row = {k.strip().lower(): v.strip() for k, v in raw_row.items() if k}

            # Map CSV fields (upload.csv format)
            first = row.get('first name', '')
            last = row.get('last name', '')
            name = (first + ' ' + last).strip() if (first or last) else row.get('name', '')
            practice = row.get('practice', row.get('practice name', ''))
            specialty_raw = row.get('specialty', '')
            address = row.get('address', '')
            city = row.get('city', '')
            state = row.get('st', row.get('state', ''))
            zip_code = row.get('zip', row.get('zip code', ''))
            phone = row.get('phone', '')
            email = row.get('email 1', row.get('email', ''))
            contact = row.get('send name', row.get('contact', ''))

            specialty_code = classify_specialty(specialty_raw)
            keep = should_keep(specialty_code)

            parsed = {
                'name': name.strip(),
                'practice_name': practice.strip(),
                'specialty_raw': specialty_raw.strip(),
                'specialty_code': specialty_code,
                'address': address.strip(),
                'city': city.strip(),
                'state': state.strip(),
                'zip_code': zip_code.strip(),
                'phone': phone.strip(),
                'email': email.strip(),
                'contact_person': contact.strip(),
                'keep': keep,
            }
            rows.append(parsed)
            if keep:
                keep_count += 1
            else:
                filter_count += 1

        # Store in session for confirmation
        request.session[f'import_preview_{pk}'] = json.dumps(rows)
        request.session[f'import_filename_{pk}'] = csv_file.name

        context = {
            'client': client,
            'rows': rows,
            'keep_count': keep_count,
            'filter_count': filter_count,
            'total_count': len(rows),
            'show_preview': True,
        }
        return render(request, 'onevoice/admin/import_list.html', context)

    return render(request, 'onevoice/admin/import_list.html', {'client': client, 'show_preview': False})


# ── CSR Assignment ──

@ov_admin_required
def assign_csr(request, pk):
    client = get_object_or_404(OVClient, pk=pk)
    csrs = CustomUser.objects.filter(user_type='csr')

    if request.method == 'POST':
        csr_ids = request.POST.getlist('csrs')
        split_at = request.POST.get('split_at', '')

        client.assigned_csrs.set(csr_ids)

        # If two CSRs and split specified, assign dentists
        selected_csrs = CustomUser.objects.filter(id__in=csr_ids, user_type='csr')
        if selected_csrs.count() == 2 and split_at:
            try:
                split_at = int(split_at)
            except ValueError:
                split_at = None

            if split_at:
                csr_list = list(selected_csrs)
                dentists = list(client.dentists.exclude(status='removed').order_by('id'))
                for i, dentist in enumerate(dentists):
                    dentist.assigned_csr = csr_list[0] if i < split_at else csr_list[1]
                    dentist.save(update_fields=['assigned_csr'])
        elif selected_csrs.count() == 1:
            client.dentists.exclude(status='removed').update(assigned_csr=selected_csrs.first())

        messages.success(request, f'CSR assignment updated for {client.lab_name}.')
        return redirect('onevoice:client_detail', pk=pk)

    context = {
        'client': client,
        'csrs': csrs,
        'assigned_ids': list(client.assigned_csrs.values_list('id', flat=True)),
        'dentist_count': client.dentists.exclude(status='removed').count(),
    }
    return render(request, 'onevoice/admin/assign_csr.html', context)


# ── Postcard Library ──

@ov_admin_required
def postcard_library(request):
    if request.method == 'POST' and request.FILES.get('template_image'):
        name = request.POST.get('name', 'Untitled Design')
        image = request.FILES['template_image']
        OVPostcardDesign.objects.create(
            name=name,
            template_image=image,
            is_master_template=True,
            uploaded_by=request.user,
        )
        messages.success(request, f'Template "{name}" added to library.')
        return redirect('onevoice:postcard_library')

    templates = OVPostcardDesign.objects.filter(is_master_template=True)
    return render(request, 'onevoice/admin/postcard_library.html', {'templates': templates})


# ── Client Postcards ──

@ov_admin_required
def client_postcards(request, pk):
    client = get_object_or_404(OVClient, pk=pk)
    designs = OVPostcardDesign.objects.filter(client=client)
    master_templates = OVPostcardDesign.objects.filter(is_master_template=True)

    if request.method == 'POST':
        template_id = request.POST.get('template_id')
        if template_id:
            template = get_object_or_404(OVPostcardDesign, pk=template_id, is_master_template=True)
            OVPostcardDesign.objects.create(
                name=f'{template.name} — {client.lab_name}',
                template_image=template.template_image,
                client=client,
                status='draft',
                uploaded_by=request.user,
            )
            messages.success(request, 'Design assigned to client from template.')
            return redirect('onevoice:client_postcards', pk=pk)

    return render(request, 'onevoice/admin/client_postcards.html', {
        'client': client, 'designs': designs, 'master_templates': master_templates,
    })


# ── Postcard Unlock ──

@ov_admin_required
def postcard_unlock(request, pk):
    design = get_object_or_404(OVPostcardDesign, pk=pk)
    if request.method == 'POST':
        design.locked = False
        design.locked_at = None
        design.status = 'draft'
        design.approved_by_client = False
        design.approved_at = None
        design.save()
        messages.success(request, f'Design "{design.name}" unlocked.')
    return redirect('onevoice:client_postcards', pk=design.client_id)


# ── Postcard View / Delete ──

@ov_admin_required
def postcard_view(request, pk):
    design = get_object_or_404(OVPostcardDesign, pk=pk)
    return render(request, 'onevoice/admin/postcard_view.html', {'design': design})


@ov_admin_required
def postcard_delete(request, pk):
    design = get_object_or_404(OVPostcardDesign, pk=pk)
    if request.method == 'POST':
        redirect_url = 'onevoice:postcard_library'
        redirect_kwargs = {}
        if design.client_id:
            redirect_url = 'onevoice:client_postcards'
            redirect_kwargs = {'pk': design.client_id}
        name = design.name
        design.delete()
        messages.success(request, f'Postcard "{name}" deleted.')
        return redirect(redirect_url, **redirect_kwargs)
    return redirect('onevoice:postcard_library')


# ── Client Inventory ──

@ov_admin_required
def client_inventory(request, pk):
    client = get_object_or_404(OVClient, pk=pk)
    inventory = OVPostcardInventory.objects.filter(client=client).select_related('design')

    if request.method == 'POST':
        inv_id = request.POST.get('inventory_id')
        quantity = request.POST.get('quantity')
        threshold = request.POST.get('threshold')
        if inv_id:
            inv = get_object_or_404(OVPostcardInventory, pk=inv_id, client=client)
            if quantity:
                inv.quantity_on_hand = int(quantity)
                inv.last_restocked = timezone.now()
            if threshold:
                inv.reorder_threshold = int(threshold)
            inv.save()
            messages.success(request, 'Inventory updated.')
            return redirect('onevoice:client_inventory', pk=pk)

    return render(request, 'onevoice/admin/client_inventory.html', {
        'client': client, 'inventory': inventory,
    })


# ── Client Schedule ──

@ov_admin_required
def client_schedule(request, pk):
    client = get_object_or_404(OVClient, pk=pk)
    from onevoice.forms import OVMailingScheduleForm, OVCallSessionForm

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        if form_type == 'mailing':
            form = OVMailingScheduleForm(request.POST)
            if form.is_valid():
                mailing = form.save(commit=False)
                mailing.client = client
                mailing.save()
                messages.success(request, 'Mailing scheduled.')
                return redirect('onevoice:client_schedule', pk=pk)
        elif form_type == 'session':
            form = OVCallSessionForm(request.POST)
            if form.is_valid():
                session = form.save(commit=False)
                session.client = client
                session.save()
                messages.success(request, 'Call session scheduled.')
                return redirect('onevoice:client_schedule', pk=pk)

    mailings = client.mailing_schedule.all()
    sessions = client.call_sessions.all()
    mailing_form = OVMailingScheduleForm()
    session_form = OVCallSessionForm()

    csrs = CustomUser.objects.filter(user_type='csr')

    return render(request, 'onevoice/admin/client_schedule.html', {
        'client': client,
        'mailings': mailings,
        'sessions': sessions,
        'mailing_form': mailing_form,
        'session_form': session_form,
        'csrs': csrs,
    })


# ── Edit Call Session ──

@ov_admin_required
def edit_call_session(request, pk):
    session = get_object_or_404(OVCallSession, pk=pk)
    from onevoice.forms import OVCallSessionEditForm

    if request.method == 'POST':
        form = OVCallSessionEditForm(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, f'Call session updated.')
            return redirect('onevoice:client_schedule', pk=session.client_id)
    else:
        form = OVCallSessionEditForm(instance=session)

    return render(request, 'onevoice/admin/edit_call_session.html', {
        'form': form, 'session': session, 'client': session.client,
    })


# ── Delete Call Session ──

@ov_admin_required
def delete_call_session(request, pk):
    session = get_object_or_404(OVCallSession, pk=pk)
    client_pk = session.client_id
    if request.method == 'POST':
        session.delete()
        messages.success(request, 'Call session deleted.')
    return redirect('onevoice:client_schedule', pk=client_pk)


# ── Client Billing ──

@ov_admin_required
def client_billing(request, pk):
    client = get_object_or_404(OVClient, pk=pk)
    snapshots = OVBillingSnapshot.objects.filter(client=client)[:12]

    context = {
        'client': client,
        'snapshots': snapshots,
        'active_count': client.get_active_dentist_count(),
        'included_size': client.mailing_list_size,
        'overage': client.get_overage_count(),
        'overage_amount': client.get_overage_amount(),
    }
    return render(request, 'onevoice/admin/client_billing.html', context)


# ── Print Order (placeholder) ──

@ov_admin_required
def client_print_order(request, pk):
    client = get_object_or_404(OVClient, pk=pk)
    from onevoice.models import OVPrintOrder

    if request.method == 'POST':
        OVPrintOrder.objects.create(
            client=client,
            vendor=request.POST.get('vendor', ''),
            confirmation_number=request.POST.get('confirmation_number', ''),
            mail_date=request.POST.get('mail_date') or None,
            expected_delivery=request.POST.get('expected_delivery') or None,
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, 'Print order logged.')
        return redirect('onevoice:client_print_order', pk=pk)

    orders = OVPrintOrder.objects.filter(client=client)
    return render(request, 'onevoice/admin/client_print_order.html', {
        'client': client, 'orders': orders,
    })


# ── Reports ──

@ov_admin_required
def admin_reports(request):
    # CSR Performance
    csr_stats = CustomUser.objects.filter(user_type='csr').annotate(
        total_calls=Count('ov_call_records'),
        appointments_booked=Count('ov_booked_appointments'),
        emails_captured=Count('ov_call_records', filter=Q(ov_call_records__email_captured__gt='')),
    )

    # Client Success
    client_stats = OVClient.objects.filter(status='active').annotate(
        total_dentists=Count('dentists', filter=~Q(dentists__status='removed')),
        total_appointments=Count('appointments'),
        emails_captured=Count('dentists', filter=Q(dentists__status='email_captured')),
        cases_won=Count('appointments', filter=Q(appointments__case_status='won')),
    )

    # Program-wide
    total_calls = OVCallRecord.objects.count()
    total_appointments = OVAppointment.objects.count()
    total_emails = OVDentist.objects.filter(status='email_captured').count()
    total_cases_won = OVAppointment.objects.filter(case_status='won').count()
    call_to_appt_rate = (total_appointments / total_calls * 100) if total_calls > 0 else 0
    call_to_email_rate = (total_emails / total_calls * 100) if total_calls > 0 else 0

    context = {
        'csr_stats': csr_stats,
        'client_stats': client_stats,
        'total_active_clients': OVClient.objects.filter(status='active').count(),
        'total_appointments': total_appointments,
        'total_emails': total_emails,
        'total_cases_won': total_cases_won,
        'total_calls': total_calls,
        'call_to_appt_rate': call_to_appt_rate,
        'call_to_email_rate': call_to_email_rate,
    }
    return render(request, 'onevoice/admin/reports.html', context)


# ── Create OV Staff User ──

@ov_admin_required
def create_ov_user(request):
    from onevoice.forms import OVStaffUserForm
    if request.method == 'POST':
        form = OVStaffUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'User "{user.username}" created as {user.get_user_type_display()}.')
            return redirect('onevoice:admin_dashboard')
    else:
        form = OVStaffUserForm()

    return render(request, 'onevoice/admin/create_user.html', {'form': form})


# ── Notifications ──

@ov_admin_required
def admin_notifications(request):
    notifications = OVNotification.objects.filter(recipient=request.user).order_by('-created_at')[:50]
    if request.method == 'POST':
        notif_id = request.POST.get('mark_read')
        if notif_id:
            OVNotification.objects.filter(pk=notif_id, recipient=request.user).update(read=True)
            return redirect('onevoice:admin_notifications')

    return render(request, 'onevoice/admin/notifications.html', {'notifications': notifications})
