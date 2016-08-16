from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView, View
from allauth.socialaccount.models import SocialAccount
from hsreplaynet.games.models import GameReplay
from hsreplaynet.utils import get_uuid_object_or_404
from .models import AccountClaim, AccountDeleteRequest


class EditAccountView(LoginRequiredMixin, TemplateView):
	template_name = "account/edit.html"


class ClaimAccountView(LoginRequiredMixin, View):
	def get(self, request, id):
		claim = get_uuid_object_or_404(AccountClaim, id=id)
		if claim.token.user:
			if claim.token.user.is_fake:
				GameReplay.objects.filter(user=claim.token.user).update(user=request.user)
				# For now we just delete the fake user, because we are not using it.
				claim.token.user.delete()
			else:
				# Something's wrong. Get rid of the claim and reject the request.
				claim.delete()
				return HttpResponseForbidden("This token has already been claimed.")
		claim.token.user = request.user
		claim.token.save()
		# Replays are claimed in AuthToken post_save signal (games.models)
		claim.delete()
		msg = "You have claimed your account. Yay!"
		# XXX: using WARNING as a hack to ignore login/logout messages for now
		messages.add_message(request, messages.WARNING, msg)
		return redirect(settings.LOGIN_REDIRECT_URL)


class DeleteAccountView(LoginRequiredMixin, TemplateView):
	template_name = "account/delete.html"

	def post(self, request):
		if not request.POST.get("delete_confirm"):
			return redirect("account_delete")
		delete_request, _ = AccountDeleteRequest.objects.get_or_create(user=request.user)
		delete_request.reason = request.POST.get("delete_reason")
		delete_request.delete_replay_data = bool(request.POST.get("delete_replays"))
		delete_request.save()
		logout(self.request)
		return redirect(reverse("home"))


class MakePrimaryView(LoginRequiredMixin, View):
	def post(self, request):
		account = request.POST.get("account")
		try:
			socacc = SocialAccount.objects.get(id=account)
		except SocialAccount.DoesNotExist:
			return self.redirect()
		if socacc.user != request.user:
			# return HttpResponseForbidden("%r does not belong to you." % (socacc))
			return self.redirect()

		if socacc.provider != "battlenet":
			raise NotImplementedError("Making non-battlenet account primary is not implemented")

		request.user.username = socacc.extra_data.get("battletag", request.user.username)
		request.user.save()
		return self.redirect()

	def redirect(self):
		# Do not identify errors to avoid leaking metadata
		return redirect(reverse("socialaccount_connections"))
