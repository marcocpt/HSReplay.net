import json
import traceback
import shortuuid
from hashlib import sha1
from io import StringIO
from dateutil.parser import parse as dateutil_parse
from django.core.exceptions import ValidationError
from hearthstone.enums import CardType, GameTag
from hsreplay.dumper import parse_log
from hsreplaynet.cards.models import Card, Deck
from hsreplaynet.utils import guess_ladder_season, log
from hsreplaynet.utils.influx import influx_metric
from hsreplaynet.uploads.models import UploadEventStatus
from .models import GameReplay, GlobalGame, GlobalGamePlayer


class ProcessingError(Exception):
	pass


class ParsingError(ProcessingError):
	pass


class GameTooShort(ProcessingError):
	pass


class UnsupportedReplay(ProcessingError):
	pass


def eligible_for_unification(meta):
	return all([meta.get("game_handle"), meta.get("server_ip")])


def get_valid_match_start(match_start, upload_date):
	"""
	Returns a valid match_start value given the match_start and upload_date.
	If the upload_date is greater than the match_start, return the match_start.
	If it's greater than the match_start, return the upload_date, modified to
	use the match_start's timezone.
	"""
	if upload_date > match_start:
		return match_start

	log.info("match_start=%r>upload_date=%r - rejecting match_start", match_start, upload_date)
	return upload_date.astimezone(match_start.tzinfo)


def generate_globalgame_digest(game_tree, meta):
	game_handle = meta["game_handle"]
	server_address = meta["server_ip"]
	players = game_tree.game.players
	lo1, lo2 = players[0].account_lo, players[1].account_lo
	values = (game_handle, server_address, lo1, lo2)
	ret = "-".join(str(k) for k in values)
	return sha1(ret.encode("utf-8")).hexdigest()


def find_or_create_global_game(game_tree, meta):
	end_time = game_tree.end_time

	ladder_season = meta.get("ladder_season")
	if not ladder_season:
		ladder_season = guess_ladder_season(end_time)

	common = {
		"game_handle": meta.get("game_handle"),
		"server_address": meta.get("server_ip"),
	}
	defaults = {
		"server_port": meta.get("server_port"),
		"server_version": meta.get("server_version"),
		"game_type": meta.get("game_type", 0),
		"format": meta.get("format", 0),
		"build": meta["build"],
		"match_start": game_tree.start_time,
		"match_end": end_time,
		"brawl_season": meta.get("brawl_season", 0),
		"ladder_season": ladder_season,
		"scenario_id": meta.get("scenario_id"),
		"num_entities": len(game_tree.game.entities),
		"num_turns": game_tree.game.tags.get(GameTag.TURN),
	}

	if eligible_for_unification(meta):
		# If the globalgame is eligible for unification, generate a digest
		# and get_or_create the object
		digest = generate_globalgame_digest(game_tree, meta)
		global_game, created = GlobalGame.objects.get_or_create(
			digest=digest,
			defaults=defaults,
			**common
		)
	else:
		defaults.update(common)
		global_game = GlobalGame.objects.create(digest=None, **defaults)
		created = True

	return global_game, created


def find_or_create_replay(global_game, meta, existing_replay):
	client_handle = meta.get("client_handle") or None

	common = {
		"global_game": global_game,
		"client_handle": client_handle,
		"spectator_mode": meta.get("spectator_mode", False),
		"reconnecting": meta.get("reconnecting", False),
		"friendly_player_id": meta["friendly_player"],
	}
	defaults = {
		"shortid": shortuuid.uuid(),
		"aurora_password": meta.get("aurora_password", ""),
		"spectator_password": meta.get("spectator_password", ""),
		"resumable": meta.get("resumable"),
		"build": meta["build"],
	}

	if existing_replay:
		# We are reprocessing an existing replay, so straight up update it.
		defaults.update(common)
		for k, v in defaults.items():
			setattr(existing_replay, k, v)
		created = False
		replay = existing_replay
	elif client_handle:
		# Get or create a replay object based on our defaults
		replay, created = GameReplay.objects.get_or_create(defaults=defaults, **common)
	else:
		# The client_handle is the minimum we require to update an existing replay.
		# If we don't have it, we'll instead *always* create a new replay.
		defaults.update(common)
		replay = GameReplay.objects.create(**defaults)
		created = True

	return replay, created


def process_upload_event(upload_event):
	"""
	Wrapper around do_process_upload_event() to set the event's
	status and error/traceback as needed.
	"""
	upload_event.status = UploadEventStatus.PROCESSING
	upload_event.error = ""
	upload_event.traceback = ""
	upload_event.save()

	try:
		replay = do_process_upload_event(upload_event)
	except Exception as e:
		upload_event.error = str(e)
		upload_event.traceback = traceback.format_exc()

		# Set the upload status based on the exception
		if isinstance(e, ParsingError):
			upload_event.status = UploadEventStatus.PARSING_ERROR
		elif isinstance(e, (GameTooShort, UnsupportedReplay)):
			upload_event.status = UploadEventStatus.UNSUPPORTED
		elif isinstance(e, ValidationError):
			upload_event.status = UploadEventStatus.VALIDATION_ERROR
		else:
			upload_event.status = UploadEventStatus.SERVER_ERROR

		upload_event.save()

		if isinstance(e, GameTooShort):
			# Do not re-raise on GameTooShort
			return

		raise

	else:
		upload_event.game = replay
		upload_event.status = UploadEventStatus.SUCCESS
		upload_event.save()

	return replay


def capture_class_distribution_stats(replay):
	fields = {
		"num_turns": replay.global_game.num_turns,
		"opposing_player_deck_digest": replay.opposing_player.deck_list.digest,
		"friendly_player_deck_digest": replay.friendly_player.deck_list.digest,
	}

	tags = {
		"game_type": replay.global_game.game_type,
		"scenario_id": replay.global_game.scenario_id,
		"region": replay.friendly_player.account_hi,
		"opposing_player_rank": replay.opposing_player.rank,
		"opposing_player_class": replay.opposing_player.hero.card_class.name,
		"opposing_player_final_state": replay.opposing_player.final_state,
		"friendly_player_rank": replay.friendly_player.rank,
		"friendly_player_class": replay.friendly_player.hero.card_class.name,
		"friendly_player_final_state": replay.friendly_player.final_state,
	}

	influx_metric("replay_outcome_stats", fields=fields, **tags)


def parse_upload_event(upload_event, meta):
	orig_match_start = dateutil_parse(meta["match_start"])
	match_start = get_valid_match_start(orig_match_start, upload_event.created)
	if match_start != orig_match_start:
		upload_event.tainted = True
		upload_event.save()
	upload_event.file.open(mode="rb")
	log_bytes = upload_event.file.read()
	influx_metric("raw_power_log_upload_num_bytes", {"size": len(log_bytes)})
	if not log_bytes:
		raise ValidationError("The uploaded log file is empty.")
	log = StringIO(log_bytes.decode("utf-8"))
	upload_event.file.close()

	try:
		parser = parse_log(log, processor="GameState", date=match_start)
	except Exception as e:
		raise ParsingError(str(e))  # from e

	return parser


def validate_parser(parser, meta):
	# Validate upload
	if len(parser.games) != 1:
		raise ValidationError("Expected exactly 1 game, got %i" % (len(parser.games)))
	game_tree = parser.games[0]

	if len(game_tree.game.players) != 2:
		raise ValidationError("Expected 2 players, found %i" % (len(game_tree.game.players)))

	# If a player's name is None, this is an unsupported replay.
	for player in game_tree.game.players:
		if player.name is None:
			raise GameTooShort("The game was too short to parse correctly")

		if not player.heroes:
			raise UnsupportedReplay("No hero found for player %r" % (player.name))
		player._hero = list(player.heroes)[0]

		try:
			db_hero = Card.objects.get(id=player._hero.card_id)
		except Card.DoesNotExist:
			raise UnsupportedReplay("Hero %r not found." % (player._hero))
		if db_hero.type != CardType.HERO:
			raise ValidationError("%r is not a valid hero." % (player._hero))

	if not meta.get("friendly_player"):
		id = game_tree.guess_friendly_player()
		if not id:
			raise ValidationError("Friendly player ID not present at upload and could not guess it.")
		meta["friendly_player"] = id

	if not meta.get("build") and "stats" in meta:
		meta["build"] = meta["stats"]["meta"]["build"]

	return game_tree


def get_player_names(player):
	if not player.is_ai and " " in player.name:
		return "", player.name
	else:
		return player.name, ""


def update_global_players(global_game, game_tree, meta):
	# Fill the player metadata and objects
	for player in game_tree.game.players:
		player_meta = meta.get("player%i" % (player.player_id), {})
		decklist = player_meta.get("deck")
		if not decklist:
			decklist = [c.card_id for c in player.initial_deck if c.card_id]

		name, real_name = get_player_names(player)

		deck, _ = Deck.objects.get_or_create_from_id_list(decklist)

		common = {
			"game": global_game,
			"player_id": player.player_id,
			"account_hi": player.account_hi,
			"account_lo": player.account_lo,
		}
		defaults = {
			"is_first": player.tags.get(GameTag.FIRST_PLAYER, False),
			"is_ai": player.is_ai,
			"hero_id": player._hero.card_id,
			"hero_premium": player._hero.tags.get(GameTag.PREMIUM, False),
			"final_state": player.tags.get(GameTag.PLAYSTATE, 0),
			"deck_list": deck,
		}

		game_player, created = GlobalGamePlayer.objects.get_or_create(defaults=defaults, **common)

		update = {
			"name": name,
			"real_name": real_name,
			"rank": player_meta.get("rank"),
			"legend_rank": player_meta.get("legend_rank"),
			"stars": player_meta.get("stars"),
			"wins": player_meta.get("wins"),
			"losses": player_meta.get("losses"),
			"deck_id": player_meta.get("deck_id") or None,
			"cardback_id": player_meta.get("cardback"),
		}

		# Go through the update dict and update values on the player
		# This gets us extra data we might not have had when the player was first created
		updated = False
		for k, v in update.items():
			if v and getattr(game_player, k) != v:
				setattr(game_player, k, v)
				updated = True

		# Skip updating the deck if we already have a bigger one
		# TODO: We should make deck_list nullable and only create it here
		if not created and len(decklist) > game_player.deck_list.size():
			# XXX: Maybe we should also check friendly_player_id for good measure
			game_player.deck_list = deck
			updated = True

		if updated:
			game_player.save()


def do_process_upload_event(upload_event):
	meta = json.loads(upload_event.metadata)
	parser = parse_upload_event(upload_event, meta)
	game_tree = validate_parser(parser, meta)

	# Create/Update the global game object and its players
	global_game, created = find_or_create_global_game(game_tree, meta)
	update_global_players(global_game, game_tree, meta)

	# Create/Update the replay object itself
	replay, created = find_or_create_replay(global_game, meta, upload_event.game)

	user = upload_event.token.user if upload_event.token else None
	if user and not replay.user:
		replay.user = user
		replay.visibility = user.default_replay_visibility
	if upload_event.token:
		replay.upload_token = upload_event.token

	# Create and save hsreplay.xml file
	file = replay.save_hsreplay_xml(parser, meta)
	influx_metric("replay_xml_num_bytes", {"size": file.size})
	replay.update_final_states()
	replay.save()

	return replay
