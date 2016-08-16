from django.conf.urls import include, url
from .views import ClaimAccountView, DeleteAccountView, EditAccountView, MakePrimaryView


urlpatterns = [
	url(r"^$", EditAccountView.as_view(), name="account_edit"),
	url(r"^claim/(?P<id>[\w-]+)/$", ClaimAccountView.as_view(), name="account_claim"),
	url(r"^delete/$", DeleteAccountView.as_view(), name="account_delete"),
	url(r"^make_primary/$", MakePrimaryView.as_view(), name="socialaccount_make_primary"),
	url(r"^", include("allauth.urls")),
]
