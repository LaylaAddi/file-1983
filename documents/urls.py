from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    path('', views.document_list, name='list'),
    path('new/', views.document_create, name='create'),
    path('<str:document_slug>/delete/', views.document_delete, name='delete'),
    path('<str:document_slug>/wizard/', views.wizard_story, name='wizard_story'),
    path('<str:document_slug>/wizard/summary/', views.wizard_extraction_summary, name='wizard_summary'),
    path('<str:document_slug>/wizard/step1/', views.wizard_step1, name='wizard_step1'),
    path('<str:document_slug>/wizard/step2/', views.wizard_step2, name='wizard_step2'),
    path('<str:document_slug>/wizard/step3/', views.wizard_step3, name='wizard_step3'),
    path('<str:document_slug>/wizard/step4/', views.wizard_step4, name='wizard_step4'),
    path('<str:document_slug>/wizard/step5/', views.wizard_step5, name='wizard_step5'),
    path('<str:document_slug>/wizard/step6/', views.wizard_step6, name='wizard_step6'),
    path('<str:document_slug>/wizard/step7/', views.wizard_step7, name='wizard_step7'),
    path('<str:document_slug>/wizard/caselaw/', views.wizard_caselaw_strategy, name='wizard_caselaw_strategy'),
    path('lookup-district-court/', views.lookup_district_court, name='lookup_district_court'),
]
