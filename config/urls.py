from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include, reverse
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

from documents import views as document_views
from public_pages.sitemaps import SITEMAPS


def redirect_to_home(request, exception=None):
    return redirect(reverse('home'))


handler404 = redirect_to_home

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),

    # SEO
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='sitemap'),

    # PWA service worker — served from root so it can claim the whole origin.
    path('sw.js', document_views.service_worker, name='service_worker'),

    # Web apps
    path('', include('public_pages.urls')),
    path('accounts/', include('accounts.urls')),
    path('documents/', include('documents.urls')),
    path('partner/', document_views.partner_dashboard, name='partner_dashboard'),
    path('partner/request-payout/', document_views.partner_request_payout, name='partner_request_payout'),

    # Stripe webhook — must be CSRF-exempt; signature verification replaces it
    path('stripe/webhook/', csrf_exempt(document_views.stripe_webhook), name='stripe_webhook'),

    # API v1
    path('api/v1/', include('config.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
