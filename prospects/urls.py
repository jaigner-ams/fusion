from django.urls import path
from . import views

app_name = 'prospects'

urlpatterns = [
    path('', views.prospect_list, name='prospect_list'),
    path('add/', views.prospect_add, name='prospect_add'),
    path('export/', views.export_csv, name='export_csv'),
    path('contacts/', views.contact_schedule, name='contact_schedule'),
    path('caller/', views.caller_dashboard, name='caller_dashboard'),
    path('caller/<int:pk>/', views.caller_detail, name='caller_detail'),
    path('caller/<int:pk>/edit/', views.caller_edit, name='caller_edit'),
    path('caller/referral/<int:pk>/edit/', views.caller_edit_referral, name='caller_edit_referral'),
    path('caller/referral/<int:pk>/delete/', views.caller_delete_referral, name='caller_delete_referral'),
    path('caller/note/<int:pk>/edit/', views.caller_edit_note, name='caller_edit_note'),
    path('caller/note/<int:pk>/delete/', views.caller_delete_note, name='caller_delete_note'),
    path('leads/', views.lead_referrals, name='lead_referrals'),
    path('caller-activity/', views.caller_activity, name='caller_activity'),
    path('<int:pk>/', views.prospect_detail, name='prospect_detail'),
    path('<int:pk>/edit/', views.prospect_edit, name='prospect_edit'),
    path('<int:pk>/delete/', views.prospect_delete, name='prospect_delete'),
    path('<int:pk>/print/', views.prospect_print, name='prospect_print'),
    path('<int:pk>/create-account/', views.create_lab_account, name='create_lab_account'),
    path('<int:pk>/send-fusion-email/', views.send_fusion_email, name='send_fusion_email'),
    path('api/taken-times/', views.taken_times_api, name='taken_times_api'),
]
