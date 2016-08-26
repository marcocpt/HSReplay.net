from django.conf import settings
from django.conf.urls import include, url
from django.views.generic import TemplateView
from .games.views import ReplayDetailView


urlpatterns = [
	url(r"^$", TemplateView.as_view(template_name="home.html"), name="home"),
	url(r"^api/", include("hsreplaynet.api.urls")),
	url(r"^account/", include("allauth.urls")),
	url(r"^account/", include("hsreplaynet.accounts.urls")),
	url(r"^games/", include("hsreplaynet.games.urls")),
	url(r"^scenarios/", include("hsreplaynet.scenarios.urls")),
	url(r"^uploads/", include("hsreplaynet.uploads.urls")),

	# Direct link to replays
	url(r"^replay/(?P<id>\w+)$", ReplayDetailView.as_view(), name="games_replay_view"),
]

if not settings.ENV_LAMBDA:
	from django.contrib.flatpages.views import flatpage
	# Do not register admin/flatpages on Lambda as they are not installed
	urlpatterns += [
		url(r"^admin/", include("hsreplaynet.admin.urls")),
		url(r"^about/privacy/$", flatpage, {"url": "/about/privacy/"}, name="privacy_policy"),
		url(r"^about/tos/$", flatpage, {"url": "/about/tos/"}, name="terms_of_service"),
		url(r"^pages/", include("django.contrib.flatpages.urls")),
	]

if settings.DEBUG:
	from django.conf.urls.static import static

	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
