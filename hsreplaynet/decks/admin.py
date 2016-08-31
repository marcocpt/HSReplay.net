from django.contrib import admin
from hsreplaynet.utils.admin import admin_urlify as urlify
from .models import Deck


@admin.register(Deck)
class PackAdmin(admin.ModelAdmin):
	date_hierarchy = "created"
	list_display = ("__str__", "type", "wild", "source_type", urlify("user"))
	list_filter = ("type", "wild", "source_type")
	raw_id_fields = ("user", "cards")
	search_fields = ("name", "user__username")
