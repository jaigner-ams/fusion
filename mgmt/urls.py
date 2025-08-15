from django.urls import path
from . import views

urlpatterns = [
    path('', views.price_management_view, name='price_management'),
    path('default-prices/', views.default_prices_view, name='default_prices'),
    path('add-dentist/', views.add_dentist_view, name='add_dentist'),
    path('dentist/<int:dentist_id>/prices/', views.dentist_prices_view, name='dentist_prices'),
    path('dentist/<int:dentist_id>/delete/', views.delete_dentist_view, name='delete_dentist'),
]