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
]