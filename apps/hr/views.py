from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from .models import Department, JobPosition, LeaveType, Employee, TimeOffRequest
from .forms import DepartmentForm, JobPositionForm, LeaveTypeForm, EmployeeForm, TimeOffRequestForm

# ==========================================
# MASTER DATA VIEWS (Depts, Roles, Leave Types)
# ==========================================

@login_required
def hr_dashboard(request):
    """ Central hub for HR Master Data """
    context = {
        'departments': Department.objects.all(),
        'positions': JobPosition.objects.all(),
        'leave_types': LeaveType.objects.all(),
        'dept_form': DepartmentForm(),
        'pos_form': JobPositionForm(),
        'leave_form': LeaveTypeForm(),
    }
    
    if request.method == 'POST':
        if 'add_dept' in request.POST:
            form = DepartmentForm(request.POST)
            if form.is_valid(): form.save()
        elif 'add_pos' in request.POST:
            form = JobPositionForm(request.POST)
            if form.is_valid(): form.save()
        elif 'add_leave' in request.POST:
            form = LeaveTypeForm(request.POST)
            if form.is_valid(): form.save()
        return redirect('hr_dashboard')
        
    return render(request, 'hr/dashboard.html', context)

# ==========================================
# EMPLOYEE DIRECTORY VIEWS
# ==========================================

@login_required
def employee_list(request):
    employees = Employee.objects.all().order_by('-hire_date')
    return render(request, 'hr/employee_list.html', {'employees': employees})

@login_required
def employee_create(request):
    if request.method == 'POST':
        form = EmployeeForm(request.POST)
        if form.is_valid():
            emp = form.save()
            messages.success(request, f"Employee {emp.full_name} onboarded successfully.")
            return redirect('employee_list')
    else:
        form = EmployeeForm()
    return render(request, 'hr/employee_form.html', {'form': form})

@login_required
def employee_detail(request, emp_id):
    employee = get_object_or_404(Employee, emp_id=emp_id)
    return render(request, 'hr/employee_detail.html', {'employee': employee})

# ==========================================
# TIME OFF / LEAVE MANAGEMENT VIEWS
# ==========================================

@login_required
def time_off_list(request):
    requests = TimeOffRequest.objects.all().order_by('-date_requested')
    return render(request, 'hr/time_off_list.html', {'requests': requests})

@login_required
def time_off_request(request):
    if request.method == 'POST':
        form = TimeOffRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.state = 'submitted'
            req.save()
            messages.success(request, "Time off request submitted for approval.")
            return redirect('time_off_list')
    else:
        form = TimeOffRequestForm()
    return render(request, 'hr/time_off_form.html', {'form': form})

@login_required
def time_off_action(request, req_id, action):
    req = get_object_or_404(TimeOffRequest, req_id=req_id)
    

    has_permission = request.user.is_superuser
    
    if not has_permission and hasattr(request.user, 'employee_profile'):

        if req.employee.manager == request.user.employee_profile:
            has_permission = True
            
    if not has_permission:
        messages.error(request, "Permission Denied: Only the assigned manager can approve this request.")
        return redirect('time_off_list')


    if action == 'approve':
        req.state = 'approved'
        messages.success(request, f"Request {req.req_id} approved.")
    elif action == 'reject':
        req.state = 'rejected'
        messages.error(request, f"Request {req.req_id} rejected.")
    
    req.save()
    return redirect('time_off_list')