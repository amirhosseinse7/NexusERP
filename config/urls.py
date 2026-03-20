from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

# ---  REST API IMPORTS ---
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from apps.logistics.api import SalesOrderViewSet

# Initialize the API Router
api_router = DefaultRouter()
api_router.register(r'sales-orders', SalesOrderViewSet, basename='api-sales-order')

# --- CORE APPS ---
from apps.core.views import (
    dashboard, partner_list, partner_create, partner_detail, 
    partner_edit, partner_csv, partner_pdf, partner_specific_csv,
    saas_dashboard, saas_company_create, saas_company_detail,
    workspace_settings, workspace_users, workspace_sequences, workspace_roles
)

# --- INVENTORY APPS ---
from apps.inventory.views import (
    product_list, product_create, product_detail, product_edit, product_label_pdf,
    location_list, location_create, location_detail,
    stock_moves, adjustment_list, adjustment_create, adjustment_detail,
    picking_list, picking_validate
)

# --- LOGISTICS APPS ---
from apps.logistics.views import (
    po_list, po_create, po_detail, po_pdf,
    so_list, so_create, so_detail, so_pdf, so_line_delete
)

# --- FINANCE APPS ---
from apps.finance.views import (
    general_ledger, general_ledger_export, general_ledger_pdf,
    invoice_list, invoice_detail, financial_reports, invoice_pdf
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('', dashboard, name='home'),
    
    # ==========================
    # REST API ENDPOINTS
    # ==========================
    path('api/v1/', include(api_router.urls)),
    path('api/v1/auth/login/', obtain_auth_token, name='api_token_auth'),
    
    # ==========================
    # SAAS SUPER ADMIN
    # ==========================
    path('saas/', saas_dashboard, name='saas_dashboard'),
    path('saas/provision/', saas_company_create, name='saas_company_create'),
    path('saas/<int:company_id>/', saas_company_detail, name='saas_company_detail'),
    
    # ==========================
    # WORKSPACE SETTINGS (TENANT ADMIN)
    # ==========================
    path('workspace/', workspace_settings, name='workspace_settings'),
    path('workspace/users/', workspace_users, name='workspace_users'),
    path('workspace/roles/', workspace_roles, name='workspace_roles'),
    path('workspace/sequences/', workspace_sequences, name='workspace_sequences'),
    
    path('store/', include('apps.store.urls')),
    path('crm/', include('apps.crm.urls')),
    path('mrp/', include('apps.mrp.urls')),
    path('hr/', include('apps.hr.urls')),

    # ==========================
    # PARTNERS
    # ==========================
    path('partners/', partner_list, name='partner_list'),
    path('partners/new/', partner_create, name='partner_create'),
    
    path('partners/export/csv/', partner_csv, name='partner_csv'),
    path('partners/export/pdf/', partner_pdf, name='partner_pdf'),
    path('partners/<str:partner_id>/export/csv/', partner_specific_csv, name='partner_specific_csv'),
    
    path('partners/<str:partner_id>/', partner_detail, name='partner_detail'),
    path('partners/<str:partner_id>/edit/', partner_edit, name='partner_edit'),

    # ==========================
    # INVENTORY
    # ==========================
    path('inventory/', product_list, name='inventory_list'),
    path('inventory/create/', product_create, name='product_create'),
    path('inventory/product/<str:sku>/', product_detail, name='product_detail'),
    path('inventory/product/<str:sku>/edit/', product_edit, name='product_edit'),
    path('inventory/product/<str:sku>/label/', product_label_pdf, name='product_label_pdf'),
    
    path('inventory/warehouses/', location_list, name='location_list'),
    path('inventory/warehouses/add/', location_create, name='location_create'),
    path('inventory/warehouses/<str:location_id>/', location_detail, name='location_detail'),
    
    path('inventory/moves/', stock_moves, name='stock_moves'),
    path('inventory/operations/', picking_list, name='picking_list'),
    path('inventory/operations/<str:picking_id>/validate/', picking_validate, name='picking_validate'),
    
    path('inventory/adjustments/', adjustment_list, name='adjustment_list'),
    path('inventory/adjustments/new/', adjustment_create, name='adjustment_create'),
    path('inventory/adjustments/<str:ref>/', adjustment_detail, name='adjustment_detail'),

    # ==========================
    # PROCUREMENT
    # ==========================
    path('purchase/', po_list, name='po_list'),      
    path('purchase/new/', po_create, name='po_create'),
    path('purchase/<str:po_id>/', po_detail, name='po_detail'),
    path('purchase/<str:po_id>/pdf/', po_pdf, name='po_pdf'),

    # ==========================
    # SALES
    # ==========================
    path('sales/', so_list, name='so_list'),
    path('sales/new/', so_create, name='so_create'),
    path('sales/<str:so_id>/', so_detail, name='so_detail'),
    path('sales/<str:so_id>/pdf/', so_pdf, name='so_pdf'),
    path('sales/<str:so_id>/line/<int:line_id>/delete/', so_line_delete, name='so_line_delete'),

    # ==========================
    # FINANCE & ACCOUNTING
    # ==========================
    path('accounting/', general_ledger, name='general_ledger'),
    path('accounting/export/csv/', general_ledger_export, name='general_ledger_export'),
    path('accounting/export/pdf/', general_ledger_pdf, name='general_ledger_pdf'),
    path('accounting/invoices/', invoice_list, name='invoice_list'),
    path('accounting/invoices/<str:invoice_id>/', invoice_detail, name='invoice_detail'),
    path('accounting/reports/', financial_reports, name='financial_reports'),
    path('invoice/<str:invoice_id>/pdf/', invoice_pdf, name='invoice_pdf'),
]