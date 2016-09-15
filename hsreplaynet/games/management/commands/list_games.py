from django.core.management.base import BaseCommand
from ...models import GameReplay


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument(
			"--limit", nargs="?", type=int,
			help="Limit total results"
		)
		parser.add_argument(
			"--username", nargs="?", type=str,
			help="Filter by username"
		)
		parser.add_argument(
			"--scenario", nargs="?", type=int,
			help="Filter by scenario ID"
		)
		parser.add_argument(
			"--uploads", action="store_true",
			help="List upload Power.log instead of hsreplay.xml file"
		)

	def handle(self, *args, **options):
		games = GameReplay.objects.all()
		scenario = options["scenario"]
		if scenario:
			games = games.filter(global_game__scenario_id=scenario)

		username = options["username"]
		if username:
			games = games.filter(user__username=username)

		limit = options["limit"]
		if limit:
			games = games[:limit]

		if options["uploads"]:
			results = games.values_list("uploads__file")
		else:
			results = games.values_list("replay_xml")

		for (path, ) in results:
			print(path)
