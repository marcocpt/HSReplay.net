from django.conf.urls import url
from .views import UploadDetailView, list_upload_failures, reprocess_failed_upload


urlpatterns = [
	url(r"^failures/$", list_upload_failures, name="failures_list"),
	url(r"^failures/(?P<shortid>[\w-]+)/$", reprocess_failed_upload, name="reprocess_failed_upload"),
	url(r"^upload/(?P<shortid>[\w-]+)/$", UploadDetailView.as_view(), name="upload_detail"),
]
