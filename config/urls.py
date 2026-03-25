from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),

    # Web apps
    path('', include('public_pages.urls')),
    path('accounts/', include('accounts.urls')),
    path('documents/', include('documents.urls')),

    # API v1
    path('api/v1/', include('config.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
