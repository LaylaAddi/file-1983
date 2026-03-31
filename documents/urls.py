from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='list'),
    path('new/', views.document_create, name='create'),
    path('<str:document_slug>/wizard/', views.wizard_story, name='wizard_story'),
]
