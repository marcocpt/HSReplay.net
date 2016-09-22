from collections import defaultdict
from enum import IntEnum
from django.db import models
from hsreplaynet.utils.fields import IntEnumField
from hsreplaynet.games.models import GameReplay
from hearthstone.enums import PlayState


class AdventureMode(IntEnum):
	# From ADVENTURE_MODE.xml
	NORMAL = 1
	EXPERT = 2
	HEROIC = 3
	CLASS_CHALLENGE = 4


class Adventure(models.Model):
	note_desc = models.CharField(max_length=64)
	name = models.CharField(max_length=64)
	sort_order = models.PositiveIntegerField(default=0)
	leaving_soon = models.BooleanField(default=False)

	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	build = models.PositiveIntegerField()

	dbf_columns = ["ID", "NOTE_DESC", "NAME", "SORT_ORDER", "LEAVING_SOON"]

	def __str__(self):
		return self.name or self.note_desc


class Wing(models.Model):
	note_desc = models.CharField(max_length=64)
	adventure = models.ForeignKey(Adventure, on_delete=models.PROTECT)
	sort_order = models.PositiveIntegerField()
	release = models.CharField(max_length=16)
	required_event = models.CharField(max_length=16)
	ownership_prereq_wing = models.ForeignKey("Wing", models.SET_NULL, null=True, blank=True)
	name = models.CharField(max_length=64)
	coming_soon_label = models.CharField(max_length=64)
	requires_label = models.CharField(max_length=64)

	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	build = models.PositiveIntegerField()

	dbf_columns = [
		"ID", "NOTE_DESC", "ADVENTURE_ID", "SORT_ORDER", "RELEASE", "REQUIRED_EVENT",
		"OWNERSHIP_PREREQ_WING_ID", "NAME", "COMING_SOON_LABEL", "REQUIRES_LABEL",
	]

	def __str__(self):
		return self.name or self.note_desc


class Scenario(models.Model):
	note_desc = models.CharField(max_length=64)
	players = models.PositiveSmallIntegerField()
	player1_hero_card_id = models.IntegerField(null=True)
	player2_hero_card_id = models.IntegerField(null=True)
	is_tutorial = models.BooleanField(default=False)
	is_expert = models.BooleanField(default=False)
	is_coop = models.BooleanField(default=False)
	adventure = models.ForeignKey(Adventure, models.SET_NULL, null=True, blank=True)
	wing = models.ForeignKey(Wing, models.SET_NULL, null=True, blank=True)
	sort_order = models.PositiveIntegerField(default=0)
	mode = IntEnumField(enum=AdventureMode, default=0)
	client_player2_hero_card_id = models.IntegerField(null=True)
	name = models.CharField(max_length=64)
	description = models.TextField()
	opponent_name = models.CharField(max_length=64)
	completed_description = models.TextField()
	player1_deck_id = models.IntegerField(null=True)

	created = models.DateTimeField(auto_now_add=True)
	updated = models.DateTimeField(auto_now=True)
	build = models.PositiveIntegerField()

	dbf_columns = [
		"ID", "NOTE_DESC", "PLAYERS", "PLAYER1_HERO_CARD_ID", "IS_TUTORIAL",
		"IS_EXPERT", "IS_COOP", "ADVENTURE_ID", "WING_ID", "SORT_ORDER",
		("MODE_ID", "mode"), "CLIENT_PLAYER2_HERO_CARD_ID", "NAME", "DESCRIPTION",
		"OPPONENT_NAME", "COMPLETED_DESCRIPTION", "PLAYER1_DECK_ID",
	]

	def __str__(self):
		return self.name or self.note_desc

	@staticmethod
	def ai_deck_list(scenario_id):
		""" Return the AIs card list as determined across all games played."""
		deck = defaultdict(int)

		# Only examine this many games to make it perform faster
		sample_size = 20
		replays = GameReplay.objects.filter(global_game__scenario_id=scenario_id)[:sample_size]
		for replay in replays:
			for include in replay.opposing_player.deck_list.includes.all():
				card = include.card
				current_count = deck[card]
				if include.count > current_count:
					deck[card] = include.count

		alpha_sorted = sorted(deck.keys(), key=lambda c: c.name)
		mana_sorted = sorted(alpha_sorted, key=lambda c: c.cost)

		result = []
		for card in mana_sorted:
			for i in range(0, deck[card]):
				result.append(card)

		return result

	@staticmethod
	def winning_decks(scenario_id):
		""" Returns a list like:
		[
			{
				"deck": <Deck>,
				"num_wins": 23,
				# These are sorted in fastest order
				"fastest_wins": [<Replay>, <Replay>, ...]
			},
			{
				"deck": <Deck>,
				"num_wins": 19,
				# These are sorted in fastest order
				"fastest_wins": [<Replay>, <Replay>, ...]
			},
			...
		]

		The top level list elements are sorted by the deck with the most wins,
		and the "fastest_wins" element is sorted in order of the wins which
		took the least number of turns.
		"""

		complete_replays = []
		for replay in GameReplay.objects.filter(global_game__scenario_id=scenario_id).all():
			if replay.friendly_player.final_state == PlayState.WON:
				if replay.friendly_player.deck_list.size() == 30:
					complete_replays.append(replay)

		all_decks = defaultdict(dict)

		# Sort all the examples by match start so that the first example
		# of a win is selected if there are many.
		for replay in sorted(complete_replays, key=lambda r: r.global_game.match_start):

			current_winning_deck = all_decks[replay.friendly_player.deck_list]
			if "num_wins" in current_winning_deck:
				current_winning_deck["num_wins"] += 1
			else:
				current_winning_deck["num_wins"] = 1

			if "fastest_wins" in current_winning_deck:
				fastest_wins = current_winning_deck["fastest_wins"]
			else:
				fastest_wins = defaultdict(list)
				current_winning_deck["fastest_wins"] = fastest_wins

			fastest_wins[replay.global_game.num_turns].append(replay)

		result = []

		for deck, meta in sorted(all_decks.items(), key=lambda t: t[1]["num_wins"], reverse=True):
			current_result = {
				"deck": deck,
				"num_wins": meta["num_wins"],
				"fastest_wins": []
			}

			for turns, replays in sorted(meta["fastest_wins"].items(), key=lambda t: t[0]):
				current_result["fastest_wins"].extend(replays)

			result.append(current_result)

		return result
