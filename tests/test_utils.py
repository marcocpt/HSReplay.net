from hsreplaynet.utils.templatetags.web_extras import static_absolute
from django.template.context import RequestContext


def mock_context(mocker):
	request = mocker.patch("django.http.request.HttpRequest")
	request.scheme = "https"
	request.get_host.return_value = "hsreplay.net"

	context = RequestContext(request)
	return context

def test_static_absolute_with_relative_url(mocker, settings):
	settings.STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
	settings.STATIC_URL = "https://static.hsreplay.net/"
	assert static_absolute(mock_context(mocker), "resource.png") == "https://hsreplay.net/static/resource.png"

def test_static_absolute_with_absolute_url(mocker, settings):
	settings.STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
	settings.STATIC_URL = "https://static.hsreplay.net/"
	assert static_absolute(mock_context(mocker), "resource.png") == "https://static.hsreplay.net/resource.png"
