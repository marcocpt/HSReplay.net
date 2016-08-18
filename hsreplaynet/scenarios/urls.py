from django.conf.urls import url
from .views import ScenarioDetailsView, ScenarioListView


urlpatterns = [
	url(r"^$", ScenarioListView.as_view(), name="scenario_list_view"),
	url(
		r"^(?P<scenario_id>\d+)/$", ScenarioDetailsView.as_view(), name="scenario_details_view"
	),

]
