from django.http.response import HttpResponseBadRequest
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from hearthstone.enums import CardClass, BnetGameType
from .models import Card
from .queries import DeckWinRateQueryBuilder, CardCountersQueryBuilder
from hsreplaynet.features.decorators import view_requires_feature_access


@login_required
@view_requires_feature_access("winrates")
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
		card_names = [c.strip('"') for c in cards_param.split(",")]
		cards = []
		for name in card_names:
			card = Card.objects.get_by_partial_name(name)
			if card:
				cards.append(card)
			else:
				return HttpResponseBadRequest("Unknown card '%s'" % name)

		context["cards"] = cards
		query_builder.cards = context["cards"]

	columns, decks_by_winrate = query_builder.result()

	context["winrate_columns"] = columns
	context["decks_by_winrate"] = decks_by_winrate

	return render(request, "cards/deck_winrates.html", context)


@login_required
@view_requires_feature_access("winrates")
def counters(request):

	query_builder = CardCountersQueryBuilder()
	context = {}

	cards_param = request.GET.get("cards", "")
	if not cards_param:
		return HttpResponseBadRequest("A 'cards' query parameter is required.")

	card_names = [c.strip('"') for c in cards_param.split(",")]
	cards = []
	for name in card_names:
		card = Card.objects.get_by_partial_name(name)
		if card:
			cards.append(card)
		else:
			return HttpResponseBadRequest("Unknown card '%s'" % name)

	context["cards"] = cards
	query_builder.cards = context["cards"]

	columns, counters_by_match_count = query_builder.result()

	context["counter_deck_columns"] = columns
	context["counters_by_match_count"] = counters_by_match_count

	return render(request, "cards/deck_counters.html", context)
