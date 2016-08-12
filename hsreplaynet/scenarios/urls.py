from django.conf.urls import url
from .views import ScenarioDetailsView


urlpatterns = [
	url(r"^(?P<scenario_id>\d+)/$", ScenarioDetailsView.as_view(), name="scenario_details_view"),
]
