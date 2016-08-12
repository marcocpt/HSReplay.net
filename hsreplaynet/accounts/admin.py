from django.contrib import admin
from .models import AccountClaim, AccountDeleteRequest, User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


@admin.register(User)
class UserAdmin(BaseUserAdmin):
	change_form_template = "loginas/change_form.html"
	fieldsets = ()
	list_display = ("username", "date_joined", "last_login", "is_fake")
	list_filter = BaseUserAdmin.list_filter + ("is_fake", )


@admin.register(AccountClaim)
class AccountClaimAdmin(admin.ModelAdmin):
	list_display = ("__str__", "id", "token", "created")
	raw_id_fields = ("token", )


@admin.register(AccountDeleteRequest)
class AccountDeleteRequestAdmin(admin.ModelAdmin):
	list_display = ("__str__", "user", "created", "updated", "delete_replay_data")
	list_filter = ("delete_replay_data", )
	date_hierarchy = "created"
	raw_id_fields = ("user", )
	search_fields = ("user__username", "reason")
