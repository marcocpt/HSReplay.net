from django.conf.urls import url
from .views import winrates


urlpatterns = [
	url(r"^winrates/$", winrates, name="deck_winrates"),
]
