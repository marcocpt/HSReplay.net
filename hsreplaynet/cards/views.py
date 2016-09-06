from django.http.response import HttpResponseBadRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from hearthstone.enums import CardClass, BnetGameType
from .models import Card
from .queries import DeckWinRateQueryBuilder


@login_required
def winrates(request):

	query_builder = DeckWinRateQueryBuilder()
	context = {}

	player_class_param = request.GET.get("class", "").upper()
	if player_class_param:
		if player_class_param not in CardClass.__members__:
			return HttpResponseBadRequest("'class' must be the name of a class, e.g. 'priest'")
		else:
			context["player_class"] = CardClass[player_class_param].name
			query_builder.player_class = CardClass[player_class_param].value

	player_rank_param = request.GET.get("player_rank", "")
	if player_rank_param:
		if not player_rank_param.isnumeric():
			return HttpResponseBadRequest("'player_rank' must be numeric")
		else:
			context["max_rank"] = int(player_rank_param)
			query_builder.max_rank = context["max_rank"]

	min_games_param = request.GET.get("min_games", "")
	if min_games_param:
		if not min_games_param.isnumeric():
			return HttpResponseBadRequest("'min_games' must be numeric")
		else:
			context["min_games"] = int(min_games_param)
			query_builder.min_games = context["min_games"]

	game_type_param = request.GET.get("game_type", "").upper()
	if game_type_param:
		if game_type_param not in BnetGameType.__members__:
			return HttpResponseBadRequest(
				"'game_type' must be a value like 'bgt_ranked_standard'"
			)
		else:
			context["game_type"] = BnetGameType[game_type_param].name
			query_builder.game_type = BnetGameType[game_type_param].value

	cards_param = request.GET.get("cards", "")
	if cards_param:
		card_ids = cards_param.split(",")
		cards = list(Card.objects.filter(id__in=card_ids))

		if len(cards) != len(card_ids):
			return HttpResponseBadRequest("'cards' contained invalid Card IDs")
		else:
			context["cards"] = cards
			query_builder.cards = context["cards"]

	columns, decks_by_winrate = query_builder.result()

	context["winrate_columns"] = columns
	context["decks_by_winrate"] = decks_by_winrate

	return render(request, "cards/deck_winrates.html", context)
