from django.urls import path
from . import views

urlpatterns = [
    path('', views.opportunity_board, name='opportunity_board'),
    path('new/', views.opportunity_create, name='opportunity_create'),
    path('<str:opp_id>/', views.opportunity_detail, name='opportunity_detail'),
]