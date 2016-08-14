from django.conf.urls import include, url
from django.contrib import admin


urlpatterns = [
	url(r"^", include(admin.site.urls)),
	url(r"^loginas/", include("loginas.urls")),
	url(r"^rq/", include("django_rq_dashboard.urls")),
	url(r"^s3/", include("cloud_browser.urls_admin")),
]
