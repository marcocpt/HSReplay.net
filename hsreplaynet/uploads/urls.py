from django.conf.urls import url
from . import views


urlpatterns = [
	url(r"^failures/$", views.UploadFailuresListView.as_view(), name="failures_list"),
	url(
		r"^failures/(?P<shortid>[\w-]+)/$", views.reprocess_failed_upload,
		name="reprocess_failed_upload"
	),
	url(
		r"^upload/(?P<shortid>[\w-]+)/$", views.UploadDetailView.as_view(),
		name="upload_detail"
	),
]
