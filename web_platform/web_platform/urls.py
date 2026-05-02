from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Common bookmark / reverse-proxy path; app routes live at /
    path("platform/", RedirectView.as_view(url="/", permanent=False)),
    path("", include("trading.urls")),
]
