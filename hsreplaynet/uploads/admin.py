from django.contrib import admin
from hsreplaynet.utils.admin import admin_urlify as urlify
from .models import UploadEvent
from .processing import queue_upload_events_for_reprocessing


def queue_for_reprocessing(admin, request, queryset):
	queue_upload_events_for_reprocessing(queryset)
queue_for_reprocessing.short_description = "Queue for reprocessing"


@admin.register(UploadEvent)
class UploadEventAdmin(admin.ModelAdmin):
	actions = (queue_for_reprocessing, )
	list_display = (
		"__str__", "status", "tainted", urlify("token"),
		urlify("game"), "upload_ip", "created", "file", "user_agent"
	)
	list_filter = ("status", "tainted", "canary")
	raw_id_fields = ("token", "game")
	readonly_fields = ("created", "cloudwatch_url")
	search_fields = ("shortid", )

	def get_queryset(self, request):
		qs = super().get_queryset(request)
		return qs.prefetch_related("game__global_game__players")
