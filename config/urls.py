from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt

from documents import views as document_views

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),

    # Web apps
    path('', include('public_pages.urls')),
    path('accounts/', include('accounts.urls')),
    path('documents/', include('documents.urls')),
    path('partner/', document_views.partner_dashboard, name='partner_dashboard'),

    # Stripe webhook — must be CSRF-exempt; signature verification replaces it
    path('stripe/webhook/', csrf_exempt(document_views.stripe_webhook), name='stripe_webhook'),

    # API v1
    path('api/v1/', include('config.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
