from django import forms
from .models import Department, JobPosition, LeaveType, Employee, TimeOffRequest

class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'manager']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'placeholder': 'e.g., Sales'}),
            'manager': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
        }

class JobPositionForm(forms.ModelForm):
    class Meta:
        model = JobPosition
        fields = ['title', 'department', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'placeholder': 'e.g., Warehouse Manager'}),
            'department': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'description': forms.Textarea(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'rows': 3}),
        }

class LeaveTypeForm(forms.ModelForm):
    class Meta:
        model = LeaveType
        fields = ['name', 'days_allowed_per_year']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'days_allowed_per_year': forms.NumberInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
        }

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['first_name', 'last_name', 'email', 'phone', 'department', 'position', 'manager', 'hire_date']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'email': forms.EmailInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'phone': forms.TextInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'department': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'position': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'manager': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'hire_date': forms.DateInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'type': 'date'}),
        }

class TimeOffRequestForm(forms.ModelForm):
    class Meta:
        model = TimeOffRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'reason']
        widgets = {
            'employee': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'leave_type': forms.Select(attrs={'class': 'w-full border-gray-300 rounded-lg p-2'}),
            'start_date': forms.DateInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'type': 'date'}),
            'reason': forms.Textarea(attrs={'class': 'w-full border-gray-300 rounded-lg p-2', 'rows': 3}),
        }