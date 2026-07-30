from django.urls import path
from . import views

app_name = 'citizen_complaint'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('mine/', views.incident_list, name='list'),
    path('new/', views.incident_new, name='new'),
    path('<str:incident_slug>/agencies/', views.incident_agencies, name='agencies'),
    path('<str:incident_slug>/about-you/', views.incident_about_you, name='about_you'),
    path('<str:incident_slug>/drafts/', views.incident_drafts, name='drafts'),
    path('<str:incident_slug>/send/', views.incident_send, name='send'),
    path('<str:incident_slug>/sent/', views.incident_sent, name='sent'),
    path('<str:incident_slug>/pdf/', views.incident_pdf, name='pdf'),
]
