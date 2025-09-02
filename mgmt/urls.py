from django.urls import path
from . import views

urlpatterns = [
    path('', views.price_management_view, name='price_management'),
    path('default-prices/', views.default_prices_view, name='default_prices'),
    path('add-dentist/', views.add_dentist_view, name='add_dentist'),
    path('dentist/<int:dentist_id>/edit/', views.edit_dentist_view, name='edit_dentist'),
    path('dentist/<int:dentist_id>/prices/', views.dentist_prices_view, name='dentist_prices'),
    path('dentist/<int:dentist_id>/delete/', views.delete_dentist_view, name='delete_dentist'),
    path('dentist-dashboard/', views.dentist_dashboard_view, name='dentist_dashboard'),
    path('purchase-credits/', views.purchase_credits_view, name='purchase_credits'),
    path('purchase-history/', views.purchase_history_view, name='purchase_history'),
    path('credit-management/', views.credit_management_view, name='credit_management'),
    path('toggle-purchase/<int:purchase_id>/', views.toggle_purchase_status, name='toggle_purchase_status'),
    path('dentist/<int:dentist_id>/deduct-credits/', views.deduct_credits_view, name='deduct_credits'),
    path('undo-deduction/<int:transaction_id>/', views.undo_deduction_view, name='undo_deduction'),
    path('credit-transactions/', views.credit_transactions_view, name='credit_transactions'),
    path('dentist/<int:dentist_id>/change-password/', views.change_dentist_password_view, name='change_dentist_password'),
    path('change-password/', views.dentist_change_password_view, name='dentist_change_password'),
    path('upload-file/', views.upload_file_view, name='upload_file'),
    path('my-files/', views.dentist_file_list_view, name='dentist_file_list'),
    path('lab-files/', views.lab_file_list_view, name='lab_file_list'),
    path('download-file/<int:file_id>/', views.download_file_view, name='download_file'),
    path('stl-viewer/', views.stl_viewer, name='stl_viewer'),
]