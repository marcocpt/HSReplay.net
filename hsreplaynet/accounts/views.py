from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.timezone import now
from django.views.generic import TemplateView, View
from hsreplaynet.games.models import GameReplay
from hsreplaynet.utils import get_uuid_object_or_404
from .models import AccountClaim


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
		user = request.user
		# If we set `is_active`, the account behaves like it's banned...
		# user.is_active = False
		user.delete_account_request = now()
		if request.POST.get("delete_replays"):
			user.delete_replay_data = True
		user.save()
		logout(self.request)
		return redirect(reverse("home"))
