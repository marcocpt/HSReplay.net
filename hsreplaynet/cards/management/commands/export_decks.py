from django.core.management.base import BaseCommand
from django.db import connection
from hearthstone.enums import CardClass

QUERY = """
SELECT
	c.card_class AS "player_class", (
		SELECT string_agg(
			CASE WHEN ci.count > 1 THEN
				left(repeat(concat(ci.card_id, ', '), ci.count), -2)
			ELSE
				ci.card_id END, ', '
			) AS "deck_list"
		FROM cards_deck cd
		JOIN cards_include ci ON ci.deck_id = cd.id
		WHERE cd.id = gp.deck_list_id
	) AS "deck_list"
FROM games_globalgameplayer gp
JOIN games_globalgame gg ON gp.game_id = gg.id
JOIN card c ON gp.hero_id = c.id
WHERE gp.is_ai = FALSE
AND gg.match_start > now()- INTERVAL '%s hour'
"""


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument(
			"--lookback", default=1, type=int,
			help="The number of hours back from which we start the export"
		)
		parser.add_argument(
			"--out", default="decks.csv",
			help="The file where we will write the decks"
		)

	def handle(self, *args, **options):
		cursor = connection.cursor()
		lookback = options["lookback"]
		cursor.execute(QUERY % lookback)

		with open(options["out"], mode="wt") as out:
			for row in cursor.fetchall():
				record = "%s:%s\n" % (CardClass(row[0]).name, row[1])
				out.write(record)
