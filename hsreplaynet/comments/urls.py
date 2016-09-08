from django.conf.urls import include, url
from .api import CommentDetailView


urlpatterns = [
	url(r"^", include("django_comments.urls")),
]

api_urlpatterns = [
	url(r"^v1/comments/(?P<pk>\d+)/$", CommentDetailView.as_view()),
]
