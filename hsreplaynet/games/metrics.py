from django.utils.timezone import now
from hearthstone.enums import GameTag, BlockType, BnetGameType
from hearthstone.hslog.parser import LogParser
from hsreplaynet.utils.influx import influx_write_payload


class InfluxInstrumentedParser(LogParser):
	def __init__(self, upload_shortid, meta):
		super(InfluxInstrumentedParser, self).__init__()
		# We include the upload shortid so that we can more accurately target
		# map-reduce jobs to only process replays where the cards of interest
		# were actually played.
		self._upload_shortid = upload_shortid
		self._meta = meta
		self._payload = []

	def block_end(self, ts):
		block = super(InfluxInstrumentedParser, self).block_end(ts)
		if getattr(block, "type", 0) == BlockType.PLAY:
			self.record_play_block(block)
		return block

	def record_play_block(self, block):
		timestamp = now()
		player = self.current_game.current_player
		if not player:
			return
		player_meta = self._meta.get("player%i" % (player.player_id), {})

		if not player.starting_hero:
			return
		controller_hero = player.starting_hero.card_id
		game_type = BnetGameType(self._meta.get("game_type", 0)).name

		fields = {
			"shortid": self._upload_shortid,
			"card_id": block.entity.card_id,
			"turn": self.current_game.tags.get(GameTag.TURN, 0),
		}
		tags = {
			"game_type": game_type,
			"controller_hero": controller_hero,
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
