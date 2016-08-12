import json
from django.core.files.storage import default_storage
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.six import string_types
from rest_framework import serializers
from hsreplaynet.accounts.models import User
from hsreplaynet.games.models import GameReplay, GlobalGame, GlobalGamePlayer
from hsreplaynet.stats import models as stats_models
from hsreplaynet.uploads.models import UploadEvent
from hsreplaynet.utils import get_client_ip
from .models import AuthToken, APIKey


class DeckListField(serializers.ListField):
	child = serializers.CharField()


class SmartFileField(serializers.FileField):
	"""
	A FileField which interprets a valid string as a file path.
	Also see: serializers.FilePathField
	"""
	def to_internal_value(self, data):
		if isinstance(data, string_types):
			if default_storage.exists(data):
				return default_storage.open(data, mode="rb")
		return super(SmartFileField, self).to_internal_value(data)


class AccountClaimSerializer(serializers.Serializer):
	url = serializers.ReadOnlyField(source="get_absolute_url")


class UserSerializer(serializers.Serializer):
	id = serializers.IntegerField(read_only=True)
	username = serializers.CharField(max_length=100)

	def to_representation(self, instance):
		if instance.is_fake:
			return None
		return super().to_representation(instance)


class AuthTokenSerializer(serializers.HyperlinkedModelSerializer):
	key = serializers.UUIDField(read_only=True)
	user = UserSerializer(read_only=True)
	test_data = serializers.BooleanField(default=False)

	class Meta:
		model = AuthToken
		fields = ("key", "user", "test_data")

	def create(self, data):
		ret = super(AuthTokenSerializer, self).create(data)
		api_key = self.context["request"].api_key
		api_key.tokens.add(ret)
		ret.creation_apikey = api_key

		# Create a "fake" user to correspond to the AuthToken
		user = User.objects.create(username=str(ret.key), is_fake=True)
		ret.user = user
		ret.save()
		return ret


class APIKeySerializer(serializers.HyperlinkedModelSerializer):
	api_key = serializers.CharField(read_only=True)

	class Meta:
		model = APIKey
		fields = ("full_name", "email", "website", "api_key")


class StatsMetaSerializer(serializers.HyperlinkedModelSerializer):
	class Meta:
		model = stats_models.StatsMeta


class PlayerStatsSerializer(serializers.HyperlinkedModelSerializer):
	meta = serializers.ReadOnlyField()

	class Meta:
		model = stats_models.PlayerStats


class ArenaDraftStatsSerializer(serializers.HyperlinkedModelSerializer):
	meta = serializers.ReadOnlyField()

	class Meta:
		model = stats_models.ArenaDraftStats


class BrawlSeasonStatsSerializer(serializers.HyperlinkedModelSerializer):
	meta = serializers.ReadOnlyField()

	class Meta:
		model = stats_models.BrawlSeasonStats


class RankedSeasonStatsSerializer(serializers.HyperlinkedModelSerializer):
	meta = serializers.ReadOnlyField()

	class Meta:
		model = stats_models.RankedSeasonStats


class SnapshotStatsSerializer(serializers.Serializer):
	meta = StatsMetaSerializer()
	player_stats = PlayerStatsSerializer()
	arena_draft_stats = ArenaDraftStatsSerializer(required=False)
	brawl_season_stats = BrawlSeasonStatsSerializer(required=False)
	ranked_season_stats = RankedSeasonStatsSerializer(required=False)


class GameSerializer(serializers.Serializer):
	url = serializers.ReadOnlyField(source="get_absolute_url")


class PlayerSerializer(serializers.Serializer):
	rank = serializers.IntegerField(required=False, min_value=0, max_value=25, write_only=True)
	legend_rank = serializers.IntegerField(required=False, min_value=1, write_only=True)
	stars = serializers.IntegerField(required=False, max_value=104, write_only=True)
	wins = serializers.IntegerField(required=False, write_only=True)
	losses = serializers.IntegerField(required=False, write_only=True)
	deck = DeckListField(required=False, write_only=True)
	deck_id = serializers.IntegerField(required=False, min_value=0, write_only=True)
	cardback = serializers.IntegerField(required=False, min_value=1, write_only=True)


class UploadEventSerializer(serializers.Serializer):
	id = serializers.UUIDField(read_only=True)
	shortid = serializers.CharField(required=False)
	type = serializers.IntegerField()
	status = serializers.IntegerField(read_only=True)
	tainted = serializers.BooleanField(read_only=True)
	game = GameSerializer(read_only=True)
	stats = SnapshotStatsSerializer(required=False)
	test_data = serializers.BooleanField(default=False)

	file = SmartFileField(write_only=True)
	game_type = serializers.IntegerField(default=0, write_only=True)
	format = serializers.IntegerField(required=False, write_only=True)
	build = serializers.IntegerField(write_only=True)
	match_start = serializers.DateTimeField(write_only=True)
	friendly_player = serializers.IntegerField(
		required=False, min_value=1, max_value=2, write_only=True
	)

	queue_time = serializers.IntegerField(required=False, min_value=1, write_only=True)
	spectator_mode = serializers.BooleanField(default=False, write_only=True)
	reconnecting = serializers.BooleanField(default=False, write_only=True)
	resumable = serializers.BooleanField(required=False, write_only=True)
	server_ip = serializers.IPAddressField(required=False, write_only=True)
	server_port = serializers.IntegerField(
		required=False, min_value=1, max_value=65535, write_only=True
	)
	server_version = serializers.IntegerField(required=False, min_value=1, write_only=True)
	client_handle = serializers.IntegerField(required=False, min_value=0, write_only=True)
	game_handle = serializers.IntegerField(required=False, min_value=1, write_only=True)
	aurora_password = serializers.CharField(required=False, write_only=True)
	spectator_password = serializers.CharField(required=False, write_only=True)

	scenario_id = serializers.IntegerField(required=False, min_value=0, write_only=True)

	player1 = PlayerSerializer(required=False, write_only=True)
	player2 = PlayerSerializer(required=False, write_only=True)

	def create(self, data):
		request = self.context["request"]

		ret = UploadEvent(
			file=data.pop("file"),
			token=request.auth_token,
			api_key=request.api_key,
			type=data.pop("type"),
			test_data=data.pop("test_data"),
			upload_ip=get_client_ip(request),
		)
		if "shortid" in data:
			ret.shortid = data["shortid"]
		ret.metadata = json.dumps(data, cls=DjangoJSONEncoder)
		ret.save()

		return ret

	def update(self, event, data):
		request = self.context["request"]

		event.file = data.pop("file")
		event.token = request.auth_token
		event.api_key = request.api_key
		event.type = data.pop("type")
		event.test_data = data.pop("test_data")
		event.upload_ip = get_client_ip(request)
		event.metadata = json.dumps(data, cls=DjangoJSONEncoder)
		event.save()

		return event


class GlobalGamePlayerSerializer(serializers.ModelSerializer):
	class Meta:
		model = GlobalGamePlayer
		fields = (
			"name", "player_id", "account_hi", "account_lo", "is_ai", "is_first",
			"hero_id", "hero_premium", "final_state",
		)


class GlobalGameSerializer(serializers.ModelSerializer):
	players = GlobalGamePlayerSerializer(many=True, read_only=True)

	class Meta:
		model = GlobalGame
		fields = (
			"build", "match_start", "match_end", "game_type",
			"ladder_season", "scenario_id", "players", "num_turns"
		)


class GameReplaySerializer(serializers.ModelSerializer):
	user = UserSerializer(read_only=True)
	global_game = GlobalGameSerializer(read_only=True)

	class Meta:
		model = GameReplay
		fields = (
			"shortid", "user", "global_game", "spectator_mode", "friendly_player_id",
			"replay_xml", "build", "won", "disconnected", "reconnecting", "visibility"
		)
		lookup_field = "shortid"


# Shorter serializer for list queries

class GameReplayListSerializer(GameReplaySerializer):
	class Meta:
		model = GameReplay
		fields = (
			"shortid", "spectator_mode", "build", "won", "disconnected", "reconnecting",
			"visibility", "global_game", "user"
		)
