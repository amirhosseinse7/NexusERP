from django.urls import path
from . import views

urlpatterns = [

    path('', views.hr_dashboard, name='hr_dashboard'),
    

    path('employees/', views.employee_list, name='employee_list'),
    path('employees/new/', views.employee_create, name='employee_create'),
    path('employees/<str:emp_id>/', views.employee_detail, name='employee_detail'),
    

    path('time-off/', views.time_off_list, name='time_off_list'),
    path('time-off/request/', views.time_off_request, name='time_off_request'),
    path('time-off/<str:req_id>/<str:action>/', views.time_off_action, name='time_off_action'),
]