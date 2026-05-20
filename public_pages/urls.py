from django.urls import path
from . import views

app_name = 'public_pages'

urlpatterns = [
    path('', views.landing_page, name='home'),
    path('guide/', views.user_guide, name='user_guide'),
    path('robots.txt', views.robots_txt, name='robots_txt'),

    path('rights/', views.know_your_rights, name='know_your_rights'),
    path('rights/record-police/', views.right_to_record, name='right_to_record'),
    path('rights/section-1983/', views.section_1983, name='section_1983'),
    path('rights/violated/', views.rights_violated, name='rights_violated'),
    path('rights/first-amendment-auditors/', views.first_amendment_auditors, name='first_amendment_auditors'),
    path('rights/fourth-amendment/', views.fourth_amendment, name='fourth_amendment'),
    path('rights/fifth-amendment/', views.fifth_amendment, name='fifth_amendment'),

    # Legal pages
    path('legal/terms/', views.legal_page, {'doc_type': 'terms'}, name='terms'),
    path('legal/privacy/', views.legal_page, {'doc_type': 'privacy'}, name='privacy'),
    path('legal/disclaimer/', views.legal_page, {'doc_type': 'disclaimer'}, name='disclaimer'),
    path('legal/cookies/', views.legal_page, {'doc_type': 'cookies'}, name='cookies'),

    # CMS dynamic pages (must be last)
    path('page/<slug:slug>/', views.cms_page, name='cms_page'),
]
