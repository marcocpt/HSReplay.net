"""A module for generating Replay recommendations."""
from enum import IntEnum
from itertools import chain, islice
from hearthstone.enums import BnetGameType
from hsreplaynet.games.models import GlobalGamePlayer, Visibility


class ReplayRecommendationReason(IntEnum):
	FRIENDLY_DECK_MATCH = 0
	OPPONENT_DECK_MATCH = 1
	CLASSES_AND_RANKS_MATCH = 3
	CLASSES_AND_ARENA_KEY_MATCH = 4


class RelatedReplayRecommendation:
	def __init__(self, replay, reason):
		self.replay = replay
		self.reason = reason

	def __repr__(self):
		return "<RelatedReplayRecommendation  %s - %s>" % (self.reason.name, self.replay.pretty_name)


class RecommendationGenerator:
	"""Subclasses should supply a reason and populate recommendations during generate()"""
	reason = None

	def __init__(self, source_replay):
		self.source_replay = source_replay
		self.recommendations = []

	def __iter__(self):
		self.generate()
		return self

	def __next__(self):
		if self.recommendations:
			reco = self.recommendations.pop(0)
			return RelatedReplayRecommendation(reco, self.reason)
		raise StopIteration

	def generate(self, replay):
		raise NotImplementedError("Must be implemented by subclasses.")


class FriendlyDeckMatchGenerator(RecommendationGenerator):
	reason = ReplayRecommendationReason.FRIENDLY_DECK_MATCH

	def generate(self):
		deck = self.source_replay.friendly_player.deck_list
		account_lo = self.source_replay.friendly_player.account_lo
		for player in GlobalGamePlayer.objects.filter(deck_list=deck).exclude(account_lo=account_lo):
			related_replay = player.game.get_replay_for_global_player(player)
			if related_replay and related_replay.visibility == Visibility.Public:
				self.recommendations.append(related_replay)


class OpponentDeckMatchGenerator(RecommendationGenerator):
	reason = ReplayRecommendationReason.OPPONENT_DECK_MATCH

	def generate(self):
		deck = self.source_replay.opposing_player.deck_list
		account_lo = self.source_replay.friendly_player.account_lo
		for player in GlobalGamePlayer.objects.filter(deck_list=deck).exclude(account_lo=account_lo):
			related_replay = player.game.get_replay_for_global_player(player)
			if related_replay and related_replay.visibility == Visibility.Public:
				self.recommendations.append(related_replay)

# Generators are evaluated in order
# Thus the ordering in the lists determine which recommendations get higher priority
GENERATORS = {
	BnetGameType.BGT_UNKNOWN: [FriendlyDeckMatchGenerator],
	BnetGameType.BGT_FRIENDS: [FriendlyDeckMatchGenerator, OpponentDeckMatchGenerator],
	BnetGameType.BGT_RANKED_STANDARD: [FriendlyDeckMatchGenerator, OpponentDeckMatchGenerator],
	BnetGameType.BGT_ARENA: [FriendlyDeckMatchGenerator, OpponentDeckMatchGenerator],
	BnetGameType.BGT_VS_AI: [FriendlyDeckMatchGenerator],
	BnetGameType.BGT_CASUAL_STANDARD: [FriendlyDeckMatchGenerator, OpponentDeckMatchGenerator],
	BnetGameType.BGT_TAVERNBRAWL_PVP: [FriendlyDeckMatchGenerator, OpponentDeckMatchGenerator],
	BnetGameType.BGT_TAVERNBRAWL_1P_VERSUS_AI: [FriendlyDeckMatchGenerator],
	BnetGameType.BGT_TAVERNBRAWL_2P_COOP: [],
	BnetGameType.BGT_RANKED_WILD: [FriendlyDeckMatchGenerator, OpponentDeckMatchGenerator],
	BnetGameType.BGT_CASUAL_WILD: [FriendlyDeckMatchGenerator, OpponentDeckMatchGenerator],
}


def recommend_related_replays(replay, num):
	"""Attempts to generate up to num RelatedReplayRecommendation objects"""
	game_type = replay.global_game.game_type
	generators = [G(replay) for G in GENERATORS[game_type]]

	if generators:
		return list(islice(chain.from_iterable(generators),0, num))
	else:
		return []
