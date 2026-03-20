import csv
import random
import string
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum, F, Q, Value, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User, Permission
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist 


from apps.finance.models import JournalItem, Invoice
from apps.inventory.models import StockMove, Material
from apps.logistics.models import PurchaseOrder, SalesOrder
from apps.crm.models import Opportunity
from apps.hr.models import Employee, TimeOffRequest
from apps.mrp.models import ManufacturingOrder
from apps.core.utils import render_to_pdf
from .models import Partner, Company, UserProfile, SystemSequence, WorkspaceRole
from .forms import PartnerForm

@login_required
def dashboard(request):
    """
    The Executive Command Center.
    Pulls live data from every module in the ERP.
    """
    # --- FINANCE METRICS ---
    paid_invoices = Invoice.objects.filter(type='out_invoice', state='paid')
    total_revenue = sum(inv.total_amount for inv in paid_invoices)
    unpaid_invoices_count = Invoice.objects.filter(type='out_invoice', state='posted').count()

    # --- CRM METRICS ---
    active_opps = Opportunity.objects.exclude(state__in=['won', 'lost'])
    pipeline_value = active_opps.aggregate(Sum('expected_revenue'))['expected_revenue__sum'] or 0

    # --- LOGISTICS & MRP METRICS ---
    open_sales = SalesOrder.objects.filter(state__in=['draft', 'confirmed', 'partial']).count()
    open_purchases = PurchaseOrder.objects.filter(state__in=['draft', 'sent', 'partial']).count()
    active_manufacturing = ManufacturingOrder.objects.filter(state='confirmed').count()

    # --- HR METRICS ---
    active_employees = Employee.objects.filter(is_active=True).count()
    pending_time_off = TimeOffRequest.objects.filter(state='submitted').count()

    context = {
        'total_revenue': total_revenue,
        'unpaid_invoices_count': unpaid_invoices_count,
        'pipeline_value': pipeline_value,
        'open_sales': open_sales,
        'open_purchases': open_purchases,
        'active_manufacturing': active_manufacturing,
        'active_employees': active_employees,
        'pending_time_off': pending_time_off,
        'recent_opportunities': Opportunity.objects.all().order_by('-date_created')[:5],
        'recent_sales': SalesOrder.objects.all().order_by('-date_order')[:5],
    }
    return render(request, 'core/dashboard.html', context)

# ==========================================
# PARTNER VIEWS
# ==========================================

@login_required
@permission_required('core.view_partner', raise_exception=True)
def partner_list(request):
    partners = Partner.objects.all()
    return render(request, 'core/partner_list.html', {'partners': partners})

@login_required
@permission_required('core.add_partner', raise_exception=True)
def partner_create(request):
    if request.method == 'POST':
        form = PartnerForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('partner_list')
    else:
        form = PartnerForm()
    return render(request, 'core/partner_form.html', {'form': form, 'title': 'Add New Partner'})

@login_required
@permission_required('core.change_partner', raise_exception=True)
def partner_edit(request, partner_id):
    partner = get_object_or_404(Partner, partner_id=partner_id)
    if request.method == 'POST':
        form = PartnerForm(request.POST, instance=partner)
        if form.is_valid():
            form.save()
            return redirect('partner_detail', partner_id=partner.partner_id)
    else:
        form = PartnerForm(instance=partner)
    return render(request, 'core/partner_form.html', {'form': form, 'title': f'Edit {partner.name}'})

@login_required
@permission_required('core.view_partner', raise_exception=True)
def partner_detail(request, partner_id):
    partner = get_object_or_404(Partner, partner_id=partner_id)
    sales_orders = SalesOrder.objects.filter(customer=partner).order_by('-date_order') if partner.is_customer else []
    purchase_orders = PurchaseOrder.objects.filter(supplier=partner).order_by('-date_order') if partner.is_supplier else []
    return render(request, 'core/partner_detail.html', {
        'partner': partner,
        'sales_orders': sales_orders,
        'purchase_orders': purchase_orders
    })

# --- GENERIC EXPORTS (ALL PARTNERS) ---
@login_required
@permission_required('core.view_partner', raise_exception=True)
def partner_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="all_partners.csv"'
    writer = csv.writer(response)
    writer.writerow(['Partner ID', 'Name', 'Email', 'Phone', 'Type', 'Address'])
    
    for p in Partner.objects.all():
        ptype = "Both" if (p.is_customer and p.is_supplier) else "Customer" if p.is_customer else "Supplier" if p.is_supplier else "None"
        writer.writerow([p.partner_id, p.name, p.email, p.phone, ptype, p.address])
    return response

@login_required
@permission_required('core.view_partner', raise_exception=True)
def partner_pdf(request):
    partners = Partner.objects.all()
    return render_to_pdf('core/partner_pdf.html', {'partners': partners})


@login_required
@permission_required('core.view_partner', raise_exception=True)
def partner_specific_csv(request, partner_id):
    partner = get_object_or_404(Partner, partner_id=partner_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{partner.name}_history.csv"'
    writer = csv.writer(response)
    
    writer.writerow(['Partner ID', partner.partner_id])
    writer.writerow(['Name', partner.name])
    writer.writerow(['Contact', partner.email or 'No email'])
    writer.writerow([])
    
    writer.writerow(['Order Reference', 'Date', 'Order Type', 'Status', 'Total Items'])
    
    if partner.is_customer:
        for so in SalesOrder.objects.filter(customer=partner).order_by('-date_order'):
            writer.writerow([so.so_id, so.date_order.strftime("%Y-%m-%d"), 'Sales Order', so.state.upper(), so.lines.count()])
            
    if partner.is_supplier:
        for po in PurchaseOrder.objects.filter(supplier=partner).order_by('-date_order'):
            writer.writerow([po.po_id, po.date_order.strftime("%Y-%m-%d"), 'Purchase Order', po.state.upper(), po.lines.count()])
            
    return response

# ==========================================
# SAAS SUPER-ADMIN DASHBOARD
# ==========================================

@login_required
def saas_dashboard(request):
    """ The Master Control Panel. Only visible to Superusers. """
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied: You must be a SaaS Administrator.")
    
    companies = Company.objects.all().order_by('-created_at')
    
    for company in companies:
        company.user_count = UserProfile.objects.filter(company=company).count()
        
    total_users = User.objects.count()
        
    return render(request, 'core/saas_dashboard.html', {
        'companies': companies,
        'total_users': total_users
    })

@login_required
def saas_company_create(request):
    """ Provisions a new Workspace and generates its first Admin user. """
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied: You must be a SaaS Administrator.")
        
    if request.method == 'POST':
        company_name = request.POST.get('company_name')
        domain = request.POST.get('domain')
        admin_email = request.POST.get('admin_email')
        admin_username = request.POST.get('admin_username')
        
        with transaction.atomic():
            new_company = Company.objects.create(name=company_name, domain=domain)
            temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            user = User.objects.create_user(username=admin_username, email=admin_email, password=temp_password)
            user.is_staff = True
            user.save()
            
            UserProfile.objects.create(user=user, company=new_company)
            messages.success(request, f"WORKSPACE PROVISIONED: '{new_company.name}'. The admin user '{admin_username}' was created with temporary password: {temp_password}")
            return redirect('saas_dashboard')
            
    return render(request, 'core/saas_company_create.html')

@login_required
def saas_company_detail(request, company_id):
    """ Details of a specific tenant, allowing you to link orphaned users. """
    if not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied: You must be a SaaS Administrator.")
        
    company = get_object_or_404(Company, id=company_id)
    profiles = UserProfile.objects.filter(company=company).select_related('user', 'role')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            user_to_link = User.objects.get(username=username)
            profile, created = UserProfile.objects.get_or_create(user=user_to_link, defaults={'company': company})
            if not created:
                profile.company = company
                profile.save()
            messages.success(request, f"User '{username}' successfully linked to Workspace: {company.name}.")
        except User.DoesNotExist:
            messages.error(request, f"System Error: User '{username}' does not exist in the database.")
        return redirect('saas_company_detail', company_id=company.id)
            
    return render(request, 'core/saas_company_detail.html', {
        'company': company,
        'profiles': profiles
    })

# ==========================================
# TENANT ADMIN: WORKSPACE SETTINGS
# ==========================================

@login_required
def workspace_settings(request):
    """ General Workspace Profile Settings """
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied: Workspace Administrator only.")
        
    try:
        company = request.user.profile.company
    except ObjectDoesNotExist:
        messages.warning(request, "Global Admin Notice: Please link your account to a Tenant Workspace before accessing Workspace Settings.")
        return redirect('saas_dashboard')
        
    if request.method == 'POST':
        company.name = request.POST.get('company_name', company.name)
        company.domain = request.POST.get('domain', company.domain)
        company.save()
        messages.success(request, "Workspace profile updated successfully.")
        return redirect('workspace_settings')
        
    return render(request, 'core/workspace_settings.html', {'company': company})

@login_required
def workspace_roles(request):
    """ Create custom roles and map them to Django Permissions """
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied: Workspace Administrator only.")
        
    try:
        company = request.user.profile.company
    except ObjectDoesNotExist:
        messages.warning(request, "Global Admin Notice: Please link your account to a Tenant Workspace before accessing Roles.")
        return redirect('saas_dashboard')


    roles = WorkspaceRole.objects.all().prefetch_related('permissions')
    

    excluded_apps = ['admin', 'auth', 'contenttypes', 'sessions', 'simple_history']
    permissions = Permission.objects.exclude(content_type__app_label__in=excluded_apps).order_by('content_type__app_label', 'name')

    if request.method == 'POST':
        role_name = request.POST.get('role_name')
        description = request.POST.get('description', '')
        perm_ids = request.POST.getlist('permissions') 
        
        if role_name:
            with transaction.atomic():
                new_role = WorkspaceRole.objects.create(name=role_name, description=description)
                if perm_ids:
                    new_role.permissions.set(perm_ids)
                messages.success(request, f"Role '{role_name}' created successfully with {len(perm_ids)} permissions.")
        return redirect('workspace_roles')

    return render(request, 'core/workspace_roles.html', {'roles': roles, 'permissions': permissions})


@login_required
def workspace_users(request):
    """ Manage Workspace Users & Assign Roles """
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied: Workspace Administrator only.")
        
    try:
        company = request.user.profile.company
    except ObjectDoesNotExist:
        messages.warning(request, "Global Admin Notice: Please link your account to a Tenant Workspace before accessing Manage Users.")
        return redirect('saas_dashboard')
        
    profiles = UserProfile.objects.filter(company=company).select_related('user', 'role')
    roles = WorkspaceRole.objects.all()
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        is_admin = request.POST.get('is_admin') == 'on'
        role_id = request.POST.get('role_id')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists in the system.")
        else:
            with transaction.atomic():

                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                new_user = User.objects.create_user(username=username, email=email, password=temp_password)
                new_user.is_staff = is_admin
                new_user.save()
                

                selected_role = WorkspaceRole.objects.filter(id=role_id).first() if role_id else None
                profile = UserProfile.objects.create(user=new_user, company=company, role=selected_role)
                

                profile.sync_permissions()
                
                role_msg = f" as {selected_role.name}" if selected_role else ""
                admin_msg = " (Workspace Admin)" if is_admin else ""
                
                messages.success(request, f"User '{username}' created{role_msg}{admin_msg}! Temp Password: {temp_password}")
        return redirect('workspace_users')
        
    return render(request, 'core/workspace_users.html', {'profiles': profiles, 'roles': roles, 'company': company})

@login_required
def workspace_sequences(request):
    """ Customize Document Prefixes """
    if not request.user.is_staff and not request.user.is_superuser:
        return HttpResponseForbidden("Access Denied: Workspace Administrator only.")
        
    try:
        company = request.user.profile.company
    except ObjectDoesNotExist:
        messages.warning(request, "Global Admin Notice: Please link your account to a Tenant Workspace before accessing Document Sequences.")
        return redirect('saas_dashboard')
        
    sequences = SystemSequence.objects.all().order_by('name')
    
    if request.method == 'POST':
        seq_id = request.POST.get('seq_id')
        new_prefix = request.POST.get('prefix')
        new_padding = request.POST.get('padding')
        
        seq = SystemSequence.objects.filter(id=seq_id).first()
        if seq:
            seq.prefix = new_prefix
            seq.padding = int(new_padding)
            seq.save()
            messages.success(request, f"Prefix for '{seq.name}' updated to {new_prefix}")
        return redirect('workspace_sequences')
        
    return render(request, 'core/workspace_sequences.html', {'sequences': sequences})