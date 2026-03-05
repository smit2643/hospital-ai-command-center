from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

urlpatterns = [
    path("", include("apps.core.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.doctors.urls")),
    path("", include("apps.patients.urls")),
    path("", include("apps.documents.urls")),
    path("", include("apps.signatures.urls")),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()
