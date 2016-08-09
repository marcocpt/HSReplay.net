from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.generic import View
from hsreplaynet.uploads import processing
from .models import UploadEvent


class UploadDetailView(View):
	def get(self, request, shortid):
		try:
			upload = UploadEvent.objects.get(shortid=shortid)
		except UploadEvent.DoesNotExist:
			# It is possible the UploadEvent hasn't been created yet.
			upload = None
		else:
			if upload.game:
				return HttpResponseRedirect(upload.game.get_absolute_url())

		return render(request, "uploads/processing.html", {"upload": upload})


class UploadFailuresListView(LoginRequiredMixin, UserPassesTestMixin, View):
	template = "uploads/failures.html"
	default_limit = 50

	def test_func(self):
		return self.request.user.is_staff

	def _list_failures(self, limit):
		ret = []
		for upload in processing._list_raw_uploads_by_prefix("failed"):
			ret.append(upload)
			if len(ret) >= limit:
				break
		return ret

	def get(self, request):
		failures = self._list_failures(self.default_limit)

		return render(request, self.template, {"failures": failures})

	def post(self, request):
		results = []
		for shortid in request.POST.getlist("failure_shortid"):
			if len(shortid) < 10:
				# shortids are fairly long. Requeuing a catch-all could be dangerous.
				raise ValueError("Bad shortid: %r" % (shortid))
			prefix = "failed/%s/" % (shortid)
			result = processing._requeue_failed_raw_uploads_by_prefix(prefix)
			results.append(result)

		context = {
			"failures": self._list_failures(self.default_limit),
			"results": results,
		}
		return render(request, self.template, context)
