from django.urls import path
from . import views

urlpatterns = [
    path('buy/', views.create_web_order, name='create_web_order'),
]