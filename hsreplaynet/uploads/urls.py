from django.conf.urls import url
from . import views


urlpatterns = [
	url(
		r"^upload/(?P<shortid>[\w-]+)/$", views.UploadDetailView.as_view(),
		name="upload_detail"
	),
]
