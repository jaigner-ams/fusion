from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from onevoice.decorators import designer_required
from onevoice.models import OVPostcardDesign
from onevoice.notifications import send_ov_notification


@designer_required
def designer_dashboard(request):
    designs = OVPostcardDesign.objects.filter(
        status__in=['draft', 'pending_approval'],
        is_master_template=False,
    ).select_related('client')
    return render(request, 'onevoice/designer/dashboard.html', {'designs': designs})


@designer_required
def designer_upload(request, pk):
    design = get_object_or_404(OVPostcardDesign, pk=pk)
    if design.locked:
        messages.error(request, 'This design is locked and cannot be modified.')
        return redirect('onevoice:designer_dashboard')

    if request.method == 'POST' and request.FILES.get('customized_image'):
        design.customized_image = request.FILES['customized_image']
        design.status = 'pending_approval'
        design.uploaded_by = request.user
        design.save()

        # Notify client that design is ready for review
        if design.client and design.client.user:
            send_ov_notification(
                'list_ready', design.client.user, client=design.client,
                title=f'Postcard Design Ready for Review: {design.name}',
                message=f'Your customized postcard design "{design.name}" is ready for your review and approval.',
            )

        messages.success(request, f'Design "{design.name}" uploaded and sent for client approval.')
        return redirect('onevoice:designer_dashboard')

    return render(request, 'onevoice/designer/upload_form.html', {'design': design})
