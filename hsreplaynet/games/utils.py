from .models import GlobalGame
from django.db.models import Count


def merge_global_games(games):
	"""
	Merge a QuerySet of GlobalGame objects into a single GlobalGame.
	This will use the first GlobalGame of the iterable as the base.
	"""

	count = games.count()
	if count < 2:
		raise ValueError("Expected at least 2 GlobalGame to merge (got %i)" % (count))

	# Sanity check: Verify that the games are similar enough
	sanity_fields = ("game_handle", "digest", "server_address", "server_port", "num_turns")
	for field in sanity_fields:
		values = games.values_list(field)
		unique_values = set(k for (k, ) in values if k)
		if len(unique_values) > 1:
			raise ValueError("Can't merge mismatched GlobalGame (%s=%r)" % (field, unique_values))

	# Get the first game with exactly 2 players
	base_game = games.annotate(pc=Count("players")).filter(pc=2).first()
	assert base_game.digest
	delete = []
	for game in games.exclude(id=base_game.id):
		if not game.digest:
			print("Refusing to merge %r (no digest)" % (game))
			continue

		print("Merging %r into %r" % (game, base_game))
		for field in GlobalGame._meta.get_fields():
			oldvalue = getattr(base_game, field.name)
			value = getattr(game, field.name)
			if field.name == "id":
				delete.append(value)
			elif field.name == "players":
				value.all().delete()
			elif field.name == "replays":
				value.all().update(global_game=base_game)
			elif not game.server_version:
				# We are in spectator mode. Can't trust anything.
				continue
			elif value and value != oldvalue:
				print("Setting %r to %r (was %r)" % (field.name, value, oldvalue))
				setattr(base_game, field.name, value)

	base_game.save()
	GlobalGame.objects.filter(id__in=delete).delete()

	return base_game


def merge_all_global_games():
	games = GlobalGame.objects.exclude(digest=None).order_by()
	digests = games.values("digest").annotate(c=Count("id")).filter(c__gt=1)
	for v in digests[:10000]:
		digest = v["digest"]
		games = GlobalGame.objects.filter(digest=digest)
		print(digest, list(games))
		try:
			merge_global_games(games)
		except Exception as e:
			print("Error: %s" % (e))
			continue
