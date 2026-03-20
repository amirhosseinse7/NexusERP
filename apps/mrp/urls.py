from django.urls import path
from . import views

urlpatterns = [

    path('bom/', views.bom_list, name='bom_list'),
    path('bom/new/', views.bom_create, name='bom_create'),
    path('bom/<str:bom_id>/', views.bom_detail, name='bom_detail'),
    

    path('mo/', views.mo_list, name='mo_list'),
    path('mo/new/', views.mo_create, name='mo_create'),
    path('mo/<str:mo_id>/', views.mo_detail, name='mo_detail'),
]