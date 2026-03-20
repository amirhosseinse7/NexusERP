from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


from simple_history.models import HistoricalRecords

# ==========================================
# MASTER DATA (Dynamic Organization Structure)
# ==========================================

class Department(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., Sales, Logistics, IT")

    manager = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_departments')


    history = HistoricalRecords()

    def __str__(self):
        return self.name

class JobPosition(models.Model):
    title = models.CharField(max_length=100, unique=True, help_text="e.g., Warehouse Manager, Sales Representative")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='positions')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)


    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title} ({self.department.name})"

class LeaveType(models.Model):
    name = models.CharField(max_length=50, unique=True, help_text="e.g., Annual Leave, Sick Pay, Maternity")
    days_allowed_per_year = models.IntegerField(default=0, help_text="Set to 0 for unlimited/unpaid types")


    history = HistoricalRecords()

    def __str__(self):
        return self.name

# ==========================================
# EMPLOYEE DIRECTORY
# ==========================================

class Employee(models.Model):
    emp_id = models.CharField(max_length=50, primary_key=True, blank=True)
    

    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='employee_profile')
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)


    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    position = models.ForeignKey(JobPosition, on_delete=models.SET_NULL, null=True, blank=True)
    

    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subordinates')

    hire_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)


    history = HistoricalRecords()

    def save(self, *args, **kwargs):

        if not self.emp_id:
            from apps.core.models import SystemSequence
            self.emp_id = SystemSequence.get_next('hr.employee', 'EMP-', 4, "Employees")
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.full_name

# ==========================================
# TIME OFF / LEAVE MANAGEMENT
# ==========================================

class TimeOffRequest(models.Model):

    STATE_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Awaiting Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ]

    req_id = models.CharField(max_length=50, primary_key=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='time_off_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    
    state = models.CharField(max_length=20, choices=STATE_CHOICES, default='draft')
    date_requested = models.DateTimeField(default=timezone.now)


    history = HistoricalRecords()

    def save(self, *args, **kwargs):

        if not self.req_id:
            from apps.core.models import SystemSequence
            self.req_id = SystemSequence.get_next('hr.timeoff', 'LV-', 4, "Leave Requests")
        super().save(*args, **kwargs)

    @property
    def duration_days(self):
        
        delta = self.end_date - self.start_date
        return delta.days + 1  

    def __str__(self):
        return f"{self.req_id} - {self.employee.full_name}"