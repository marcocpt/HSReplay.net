from itertools import groupby
from django.db import connection
from .models import Deck


class DeckWinRateQueryBuilder:
	def __init__(self):
		self.cards = None
		self.player_class = None
		self.max_rank = None
		self.min_games = None
		self.game_type = None
		self.limit = 20

	def _inner_decks_query(self, cards):
		card_groups = groupby(sorted(cards, key=lambda c: c.id), key=lambda c: c.id)
		cardids_with_counts = [(k, len(list(g))) for k, g in card_groups]

		sub = '(SELECT deck_id FROM cards_include WHERE card_id = "%s" AND count >= %s)'
		from_template = " FROM %s ci0" % sub
		join_template = " JOIN " + sub + " ci%s ON ci0.deck_id = ci%s.deck_id"

		query = 'SELECT ci0.deck_id AS "id" '
		for index, (cardid, count) in enumerate(cardids_with_counts):
			if index == 0:
				query += from_template % (cardid, count)
			else:
				query += join_template % (cardid, count, index, index)
		return query

	def _generate_final_query(self):
		columns = ("num_games", "avg_rank", "win_percentage", "deck")

		select_prefix = "SELECT "

		num_games = 'count(ggp.game_id) AS "num_games", '

		avg_rank = 'round(avg(ggp.rank)) AS "avg_rank", '

		win_percentage = """
		round(100 *
			(1.0 * (
				SELECT count(*) FROM games_globalgameplayer gp
				WHERE gp.deck_list_id = d.id AND gp.final_state = 4
			)) / (
				SELECT count(*) FROM games_globalgameplayer gp WHERE
				gp.deck_list_id = d.id
			), 2
		) AS "win_percentage",
		"""

		deck_id = 'd.id as "deck" '

		if self.cards:
			from_clause = "FROM ( %s ) d" % self._inner_decks_query(self.cards)
		else:
			from_clause = "FROM cards_deck d"

		join = " JOIN games_globalgameplayer ggp ON ggp.deck_list_id = d.id"

		player_class_filter = " JOIN card c ON c.id = ggp.hero_id AND c.card_class = %s"

		game_type_filter = " JOIN games_globalgame gg ON ggp.game_id = gg.id AND " \
			"gg.game_type = %s "

		where = " WHERE (SELECT sum(count) FROM cards_include WHERE deck_id = d.id) = 30"

		player_rank_filter = " AND ggp.rank <= %s"

		group_by_clause = " GROUP BY d.id"

		min_games_filter = " HAVING count(ggp.game_id) >= %s"

		order_by_clause = ' ORDER BY "win_percentage" DESC'

		limit_clause = " LIMIT %s" % self.limit

		query_columns = select_prefix + num_games + avg_rank + win_percentage + deck_id
		query = query_columns + from_clause + join

		if self.player_class:
			query += player_class_filter % self.player_class

		if self.game_type:
			query += game_type_filter % self.game_type

		query += where

		if self.max_rank:
			query += player_rank_filter % self.max_rank

		query += group_by_clause

		if self.min_games:
			query += min_games_filter % self.min_games

		query += order_by_clause
		query += limit_clause

		return columns, query

	def result(self):
		columns, query = self._generate_final_query()

		cursor = connection.cursor()
		cursor.execute(query)

		rows = list(cursor.fetchall())
		deck_ids = [r[3] for r in rows]
		decks = {d.id: d for d in Deck.objects.filter(id__in=deck_ids).all()}

		results = []
		for row in rows:
			row = list(row)
			row[3] = str(decks[row[3]])
			results.append(row)

		return columns, results
