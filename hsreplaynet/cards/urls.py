from django.conf.urls import url
from .views import winrates, counters


urlpatterns = [
	url(r"^winrates/$", winrates, name="deck_winrates"),
	url(r"^counters/$", counters, name="deck_counters"),
]
