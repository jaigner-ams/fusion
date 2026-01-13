import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from datetime import date
from .models import Prospect, ProspectNote, ProspectServiceType
from .forms import ProspectForm, ProspectNoteForm


@login_required
def prospect_list(request):
    """List all prospects with status filter"""
    status_filter = request.GET.get('status', '')

    prospects = Prospect.objects.all()
    if status_filter:
        prospects = prospects.filter(status=status_filter)

    # Count by status for dashboard
    status_counts = {
        'prospect': Prospect.objects.filter(status='prospect').count(),
        'member': Prospect.objects.filter(status='member').count(),
        'declined': Prospect.objects.filter(status='declined').count(),
        'total': Prospect.objects.count(),
    }

    context = {
        'prospects': prospects,
        'status_filter': status_filter,
        'status_choices': Prospect.STATUS_CHOICES,
        'status_counts': status_counts,
        'title': 'Prospects List'
    }
    return render(request, 'prospects/prospect_list.html', context)


@login_required
def prospect_add(request):
    """Add a new prospect"""
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
    prospect = get_object_or_404(Prospect, pk=pk)

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
            return redirect('prospects:prospect_detail', pk=prospect.pk)
    else:
        form = ProspectForm(instance=prospect)
        # Pre-populate service types
        form.initial['service_types'] = list(
            prospect.service_types.values_list('service_type', flat=True)
        )

    context = {
        'form': form,
        'prospect': prospect,
        'title': f'Edit Prospect: {prospect.lab_name}'
    }
    return render(request, 'prospects/prospect_form.html', context)


@login_required
def prospect_detail(request, pk):
    """View prospect details with notes"""
    prospect = get_object_or_404(Prospect, pk=pk)
    notes = prospect.notes.all()
    note_form = ProspectNoteForm()

    if request.method == 'POST':
        note_form = ProspectNoteForm(request.POST)
        if note_form.is_valid():
            note = note_form.save(commit=False)
            note.prospect = prospect
            note.save()
            messages.success(request, 'Note added successfully!')
            return redirect('prospects:prospect_detail', pk=pk)

    context = {
        'prospect': prospect,
        'notes': notes,
        'note_form': note_form,
        'title': f'Prospect: {prospect.lab_name}'
    }
    return render(request, 'prospects/prospect_detail.html', context)


@login_required
def prospect_delete(request, pk):
    """Delete a prospect"""
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

    prospects = Prospect.objects.all()
    if status_filter:
        prospects = prospects.filter(status=status_filter)

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    filename = f'prospects_{date.today().isoformat()}'
    if status_filter:
        filename += f'_{status_filter}'
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'

    writer = csv.writer(response)

    # Write header row
    writer.writerow([
        'Status',
        'Lab Name',
        'Person Name',
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
            prospect.get_status_display(),
            prospect.lab_name,
            prospect.person_name,
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
