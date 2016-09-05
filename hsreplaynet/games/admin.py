from django.contrib import admin
from django.db.models import Count
from hsreplaynet.uploads.models import UploadEvent
from hsreplaynet.uploads.processing import queue_upload_event_for_reprocessing
from hsreplaynet.utils.admin import admin_urlify as urlify, set_user
from .models import GameReplay, GlobalGame, GlobalGamePlayer


def queue_for_reprocessing(admin, request, queryset):
	for obj in queryset:
		uploads = obj.uploads.all()
		if uploads:
			queue_upload_event_for_reprocessing(uploads[0])
queue_for_reprocessing.short_description = "Queue original upload for reprocessing"


class GlobalGamePlayerInline(admin.StackedInline):
	model = GlobalGamePlayer
	raw_id_fields = ("user", "hero", "deck_list")
	max_num = 2
	show_change_link = True


class UploadEventInline(admin.StackedInline):
	model = UploadEvent
	extra = 0
	raw_id_fields = ("token", )
	show_change_link = True


class GameReplayInline(admin.StackedInline):
	model = GameReplay
	extra = 0
	raw_id_fields = ("upload_token", "user")
	show_change_link = True


@admin.register(GameReplay)
class GameReplayAdmin(admin.ModelAdmin):
	actions = (set_user, queue_for_reprocessing)
	list_display = (
		"__str__", urlify("user"), urlify("global_game"), "visibility",
		"build", "client_handle", "hsreplay_version", "replay_xml",
	)
	list_filter = (
		"global_game__game_type", "hsreplay_version", "visibility",
		"won", "spectator_mode", "disconnected", "reconnecting", "is_deleted"
	)
	raw_id_fields = (
		"upload_token", "user", "global_game",
	)
	readonly_fields = ("shortid", )
	search_fields = ("shortid", "global_game__players__name", "user__username")
	inlines = (UploadEventInline, )

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		return qs.prefetch_related("global_game__players")


class ReplaySidesFilter(admin.SimpleListFilter):
	"""
	A filter to look up the amount of uploads on a GlobalGame
	"""
	title = "replay sides"
	parameter_name = "sides"

	def lookups(self, request, model_admin):
		return (0, "0 (broken)"), (1, "1 (normal)"), (2, "2 (both sides)"), (3, "3+ (?)")

	def queryset(self, request, queryset):
		queryset = queryset.annotate(sides=Count("replays"))
		value = self.value()
		if value is not None and value.isdigit():
			value = int(value)
			if value > 2:
				return queryset.filter(sides__gt=2)
			return queryset.filter(sides__exact=value)
		return queryset


@admin.register(GlobalGame)
class GlobalGameAdmin(admin.ModelAdmin):
	date_hierarchy = "match_start"
	list_display = (
		"__str__", "match_start", "game_type", "build", "server_version",
		"game_handle", "ladder_season", "scenario_id", "num_turns",
	)
	list_filter = (
		"game_type", "ladder_season", "brawl_season", "build", ReplaySidesFilter
	)
	search_fields = ("replays__shortid", "players__name")
	inlines = (GlobalGamePlayerInline, GameReplayInline)

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		return qs.prefetch_related("players")


@admin.register(GlobalGamePlayer)
class GlobalGamePlayerAdmin(admin.ModelAdmin):
	actions = (set_user, )
	list_display = ("__str__", urlify("user"), "player_id", "is_first")
	list_filter = ("is_ai", "rank", "is_first")
	raw_id_fields = ("game", "user", "deck_list")
