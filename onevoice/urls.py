from django.urls import path
from .views import admin_views, csr_views, client_views, designer_views

app_name = 'onevoice'

urlpatterns = [
    # ── Admin views ──
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/clients/', admin_views.client_list, name='client_list'),
    path('admin/clients/add/', admin_views.client_add, name='client_add'),
    path('admin/clients/<int:pk>/', admin_views.client_detail, name='client_detail'),
    path('admin/clients/<int:pk>/edit/', admin_views.client_edit, name='client_edit'),
    path('admin/clients/<int:pk>/agreement/', admin_views.send_agreement, name='send_agreement'),
    path('admin/clients/<int:pk>/import-list/', admin_views.import_dentist_list, name='import_dentist_list'),
    path('admin/clients/<int:pk>/assign-csr/', admin_views.assign_csr, name='assign_csr'),
    path('admin/clients/<int:pk>/postcards/', admin_views.client_postcards, name='client_postcards'),
    path('admin/clients/<int:pk>/inventory/', admin_views.client_inventory, name='client_inventory'),
    path('admin/clients/<int:pk>/schedule/', admin_views.client_schedule, name='client_schedule'),
    path('admin/clients/<int:pk>/billing/', admin_views.client_billing, name='client_billing'),
    path('admin/session/<int:pk>/edit/', admin_views.edit_call_session, name='edit_call_session'),
    path('admin/session/<int:pk>/delete/', admin_views.delete_call_session, name='delete_call_session'),
    path('admin/clients/<int:pk>/print-order/', admin_views.client_print_order, name='client_print_order'),
    path('admin/postcards/', admin_views.postcard_library, name='postcard_library'),
    path('admin/postcards/<int:pk>/unlock/', admin_views.postcard_unlock, name='postcard_unlock'),
    path('admin/postcards/<int:pk>/view/', admin_views.postcard_view, name='postcard_view'),
    path('admin/postcards/<int:pk>/delete/', admin_views.postcard_delete, name='postcard_delete'),
    path('admin/reports/', admin_views.admin_reports, name='admin_reports'),
    path('admin/create-user/', admin_views.create_ov_user, name='create_ov_user'),
    path('admin/users/', admin_views.user_list, name='user_list'),
    path('admin/users/<int:pk>/edit/', admin_views.user_edit, name='user_edit'),
    path('admin/notifications/', admin_views.admin_notifications, name='admin_notifications'),

    # ── CSR views ──
    path('csr/', csr_views.csr_dashboard, name='csr_dashboard'),
    path('csr/client/<int:client_pk>/', csr_views.csr_client_panel, name='csr_client_panel'),
    path('csr/client/<int:client_pk>/dentists/', csr_views.csr_dentist_list, name='csr_dentist_list'),
    path('csr/dentist/<int:pk>/', csr_views.csr_dentist_record, name='csr_dentist_record'),
    path('csr/dentist/<int:pk>/book-appointment/', csr_views.csr_book_appointment, name='csr_book_appointment'),
    path('csr/session/<int:pk>/begin/', csr_views.csr_session_begin, name='csr_session_begin'),
    path('csr/session/<int:pk>/done/', csr_views.csr_session_done, name='csr_session_done'),
    path('api/dentist-lock/<int:pk>/', csr_views.dentist_lock_api, name='dentist_lock'),
    path('api/dentist-unlock/<int:pk>/', csr_views.dentist_unlock_api, name='dentist_unlock'),

    # ── Client views ──
    path('client/', client_views.client_dashboard, name='client_dashboard'),
    path('client/prospects/', client_views.client_prospect_list, name='client_prospect_list'),
    path('client/prospects/<int:pk>/correction/', client_views.client_correction_request, name='client_correction'),
    path('client/prospects/<int:pk>/remove/', client_views.client_removal_request, name='client_removal'),
    path('client/appointments/', client_views.client_appointments, name='client_appointments'),
    path('client/appointments/previous/', client_views.client_previous_appointments, name='client_previous_appointments'),
    path('client/appointments/<int:pk>/followup/', client_views.client_followup, name='client_followup'),
    path('client/availability/', client_views.client_availability, name='client_availability'),
    path('client/postcards/', client_views.client_postcard_view, name='client_postcard_view'),
    path('client/postcards/<int:pk>/approve/', client_views.client_postcard_approve, name='client_postcard_approve'),
    path('client/postcards/<int:pk>/comment/', client_views.client_postcard_comment, name='client_postcard_comment'),
    path('client/schedule/', client_views.client_schedule_view, name='client_schedule_view'),
    path('client/agreement/<int:pk>/sign/', client_views.client_sign_agreement, name='client_sign_agreement'),
    path('client/contact/', client_views.client_contact, name='client_contact'),

    # ── Designer views ──
    path('designer/', designer_views.designer_dashboard, name='designer_dashboard'),
    path('designer/upload/<int:pk>/', designer_views.designer_upload, name='designer_upload'),
]
