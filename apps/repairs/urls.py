from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('repairs/', views.repair_list, name='repair_list'),
    path('repairs/new/', views.repair_create, name='repair_create'),
    path('repairs/<int:pk>/', views.repair_detail, name='repair_detail'),
    path('repairs/<int:pk>/edit/', views.repair_edit, name='repair_edit'),
    path('repairs/<int:pk>/delete/', views.repair_delete, name='repair_delete'),
    path('repairs/export/excel/', views.export_repairs_excel, name='export_excel'),
    path('clients/', views.client_list, name='client_list'),
    path('clients/new/', views.client_create, name='client_create'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('clients/<int:pk>/edit/', views.client_edit, name='client_edit'),
    path('clients/<int:client_pk>/device/new/', views.device_create, name='device_create'),
    path('parts/<int:pk>/delete/', views.delete_part, name='delete_part'),
    path('api/client-devices/', views.get_client_devices, name='client_devices_api'),
]
