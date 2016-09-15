from django.utils.timezone import now
from hearthstone.enums import GameTag, BlockType, BnetGameType, CardClass
from hearthstone.hslog.watcher import LogWatcher
from hsreplaynet.utils.influx import influx_write_payload
from hsreplaynet.utils.instrumentation import error_handler


class InfluxInstrumentedParser(LogWatcher):
	def __init__(self, upload_shortid, meta):
		super(InfluxInstrumentedParser, self).__init__()
		# We include the upload shortid so that we can more accurately target
		# map-reduce jobs to only process replays where the cards of interest
		# were actually played.
		self._upload_shortid = upload_shortid
		self._meta = meta
		self._payload = []

	def on_block(self, action):
		try:
			self.process_action(action)
		except Exception as e:
			error_handler(e)

	def process_action(self, action):
		if action.type != BlockType.PLAY:
			return

		timestamp = now()
		player = self.current_game.current_player
		player_meta = self._meta.get("player%i" % (player.player_id), {})

		if not player.starting_hero:
			return
		controller_class_id = player.starting_hero.tags.get(GameTag.CLASS, 0)
		controller_class = CardClass(controller_class_id).name
		game_type = BnetGameType(self._meta.get("game_type", 0)).name

		fields = {
			"shortid": self._upload_shortid,
			"card_id": action.entity.card_id,
			"turn": self.current_game.tags.get(GameTag.TURN, 0),
		}
		tags = {
			"game_type": game_type,
			"controller_class": controller_class,
			"region": player.account_hi,
			"controller_rank": player_meta.get("rank"),
		}
		payload = {
			"measurement": "cards_played_stats",
			"tags": tags,
			"fields": fields,
			"time": timestamp.isoformat()
		}

		self._payload.append(payload)

	def write_payload(self):
		influx_write_payload(self._payload)
