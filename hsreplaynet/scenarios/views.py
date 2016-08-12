from django.shortcuts import render
from django.views.generic import View
from .models import Scenario


class ScenarioDetailsView(View):
	def get(self, request, scenario_id):
		context = {
			"ai_deck_list": Scenario.ai_deck_list(scenario_id),
			"winning_decks": Scenario.winning_decks(scenario_id)
		}

		return render(request, "scenarios/scenario_details.html", context)
