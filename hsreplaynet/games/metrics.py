from hearthstone.enums import GameTag, BlockType, BnetGameType, CardClass
from hearthstone.hslog.watcher import LogWatcher
from hsreplaynet.utils.instrumentation import influx_write_payload, error_handler
from django.utils.timezone import now


class InfluxInstrumentedParser(LogWatcher):

	def __init__(self, upload_shortid, meta):
		# We include the upload shortid so that we can more accurately target
		# map-reduce jobs to only process replays where the cards of interest
		# were actually played.
		self._upload_shortid = upload_shortid
		self._meta = meta
		self._payload = []

	def on_block(self, action):
		try:
			if action.type == BlockType.PLAY:
				timestamp = now()

				player = self.current_game.current_player

				player_meta = self._meta.get("player%i" % (player.player_id), {})
				if player_meta and "rank" in player_meta:
					rank = player_meta.get("rank")
				else:
					rank = None

				if player.starting_hero:
					controller_class_id = player.starting_hero.tags.get(GameTag.CLASS, 0)
					controller_class = CardClass(controller_class_id).name
				else:
					controller_class = None

				if "game_type" in self._meta:
					game_type = BnetGameType(int(self._meta.get("game_type"))).name
				else:
					game_type = None

				fields = {
					"shortid": self._upload_shortid,
					"cardId": action.entity.card_id,
					"turn_number": self.current_game.tags.get(GameTag.TURN, -1),
				}

				tags = {
					"game_type": game_type,
					"controller_class": controller_class,
					"region": player.account_hi,
					"controller_rank": rank,
				}

				payload = {
					"measurement": "cards_played_stats",
					"tags": tags,
					"fields": fields,
					"time": timestamp.isoformat()
				}

				self._payload.append(payload)

		except Exception as e:
			error_handler(e)


	def persist_influx_payload(self):
		influx_write_payload(self._payload)
