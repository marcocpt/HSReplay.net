from django import template
from django.conf import settings
from hsreplaynet.features.models import Feature

register = template.Library()


@register.simple_tag(takes_context=True)
def feature(context, feature_name):
	"""
	Expected usage is:

	{% feature "winrates" as winrates %}
	{% if winrates.is_enabled %}
		...
		{% if winrates.read_only %} ... {% endif %}
		...
	{% endif %}
	"""
	feature_context = {
		"is_enabled": True,
		"read_only": False
	}

	if settings.DEBUG:
		# Feature policies are not enforced in development mode
		return feature_context

	user = context["request"].user

	try:
		feature = Feature.objects.get(name=feature_name)
	except Feature.DoesNotExist:
		# Missing features are treated as if they are set to FeatureStatus.STAFF_ONLY
		# Occurs when new feature code is deployed before the DB is updated
		feature_context["is_enabled"] = user.is_staff
	else:
		feature_context["is_enabled"] = feature.enabled_for_user(user)
		feature_context["read_only"] = feature.read_only

	return feature_context
