from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='list'),
    path('new/', views.document_create, name='create'),
    path('<str:document_slug>/wizard/', views.wizard_story, name='wizard_story'),
    path('<str:document_slug>/wizard/summary/', views.wizard_extraction_summary, name='wizard_summary'),
    path('<str:document_slug>/wizard/step1/', views.wizard_step1, name='wizard_step1'),
    path('<str:document_slug>/wizard/step2/', views.wizard_step2, name='wizard_step2'),
    path('<str:document_slug>/wizard/step3/', views.wizard_step3, name='wizard_step3'),
    path('<str:document_slug>/wizard/step4/', views.wizard_step4, name='wizard_step4'),
    path('lookup-district-court/', views.lookup_district_court, name='lookup_district_court'),
]
