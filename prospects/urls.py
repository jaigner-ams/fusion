from django.urls import path
from . import views

app_name = 'prospects'

urlpatterns = [
    path('', views.prospect_list, name='prospect_list'),
    path('add/', views.prospect_add, name='prospect_add'),
    path('export/', views.export_csv, name='export_csv'),
    path('contacts/', views.contact_schedule, name='contact_schedule'),
    path('<int:pk>/', views.prospect_detail, name='prospect_detail'),
    path('<int:pk>/edit/', views.prospect_edit, name='prospect_edit'),
    path('<int:pk>/delete/', views.prospect_delete, name='prospect_delete'),
    path('<int:pk>/print/', views.prospect_print, name='prospect_print'),
]
