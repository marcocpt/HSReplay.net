from django.apps import AppConfig


class AdminConfig(AppConfig):
	label = "hsreplaynet.admin"
	name = "hsreplaynet.admin"

default_app_config = "hsreplaynet.admin.AdminConfig"
