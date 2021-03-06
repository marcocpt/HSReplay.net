from django import template
from django.conf import settings
from humanize import naturaldelta, naturaltime
from datetime import datetime
from hsreplaynet.games.models import GameReplay
from re import match, IGNORECASE
from django.contrib.staticfiles.templatetags.staticfiles import static


register = template.Library()


@register.filter
def human_duration(value):
	return naturaldelta(value)


@register.filter
def human_time(value):
	return naturaltime(datetime.now(value.tzinfo) - value)


@register.simple_tag
def joust_static(path):
	return settings.JOUST_STATIC_URL + path


@register.simple_tag
def get_featured_game():
	id = getattr(settings, "FEATURED_GAME_ID", None)
	if not id:
		return

	try:
		replay = GameReplay.objects.get(shortid=id)
	except GameReplay.DoesNotExist:
		replay = None
	return replay


@register.simple_tag
def hearthstonejson(build=None, locale="enUS"):
	if not build:
		build = "latest"
	return settings.HEARTHSTONEJSON_URL % {"build": build, "locale": locale}


@register.simple_tag
def setting(name):
	return getattr(settings, name, "")


@register.simple_tag(takes_context=True)
def static_absolute(context, value):
	request = context.request
	value = static(value)
	# check whether scheme is present according to RFC 3986
	if not match("[a-z]([a-z0-9+-.])*:", value, IGNORECASE):
		value = "%s://%s%s" % (request.scheme, request.get_host(), value)
	return value
