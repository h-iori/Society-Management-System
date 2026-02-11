from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Public
    path('', views.index, name='index'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Admin URLs
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/create-owner/', views.create_owner, name='create_owner'),
    path('admin/owner/<int:pk>/update/', views.update_owner, name='update_owner'),
    path('admin/owner/<int:pk>/delete/', views.delete_owner, name='delete_owner'),
    path('admin/owners/', views.owner_list, name='owner_list'),
    path('admin/owner/<int:pk>/toggle-status/', views.toggle_owner_status, name='toggle_owner_status'),
    path('admin/create-society/', views.create_society, name='create_society'),
    path('admin/society/<int:pk>/update/', views.update_society, name='update_society'),
    path('admin/society/<int:pk>/delete/', views.delete_society, name='delete_society'),
    path('admin/societies/', views.society_list, name='society_list'),
    path('admin/create-flat/', views.create_flat, name='create_flat'),
    path('admin/flat/<int:pk>/update/', views.update_flat, name='update_flat'),
    path('admin/flat/<int:pk>/delete/', views.delete_flat, name='delete_flat'),
    path('admin/flats/', views.flat_list, name='flat_list'),
    path('admin/create-bill/', views.create_bill, name='create_bill'),
    path('admin/bill/<int:pk>/update/', views.update_bill, name='update_bill'),
    path('admin/bill/<int:pk>/delete/', views.delete_bill, name='delete_bill'),
    path('admin/bills/', views.bill_list, name='bill_list'),
    path('admin/bill/<int:pk>/toggle-status/', views.toggle_bill_status, name='toggle_bill_status'),
    
    # Owner URLs
    path('owner-dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/flats/', views.owner_flats, name='owner_flats'),
    path('owner/bills/', views.owner_bills, name='owner_bills'),
    path('owner/create-tenant/', views.create_tenant, name='create_tenant'),
    path('owner/tenants/', views.tenant_list, name='tenant_list'),
    path('owner/tenant/<int:pk>/toggle-status/', views.toggle_tenant_status, name='toggle_tenant_status'),
    path('owner/tenant/<int:pk>/update/', views.update_tenant, name='update_tenant'),
    path('owner/tenant/<int:pk>/delete/', views.delete_tenant, name='delete_tenant'),
    
    # Tenant URLs
    path('tenant-dashboard/', views.tenant_dashboard, name='tenant_dashboard'),
    path('tenant/flat/', views.tenant_flat, name='tenant_flat'),
]