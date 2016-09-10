"""
Miscellaneous middleware objects
https://docs.djangoproject.com/en/1.10/topics/http/middleware/
"""


class DoNotTrackMiddleware:
	HEADER = "HTTP_DNT"

	def process_request(self, request):
		if self.HEADER in request.META:
			request.dnt = request.META[self.HEADER] == "1"
		else:
			request.dnt = None

	def process_response(self, request, response):
		if self.HEADER in request.META:
			response["DNT"] = request.META[self.HEADER]
		return response


class SetRemoteAddrFromForwardedFor:
	"""
	Middleware that sets REMOTE_ADDR based on HTTP_X_FORWARDED_FOR, if the
	latter is set and the IP is in a set of internal IPs.

	Note that this does NOT validate HTTP_X_FORWARDED_FOR. If you're not behind
	a reverse proxy that sets HTTP_X_FORWARDED_FOR automatically, do not use
	this middleware. Anybody can spoof the value of HTTP_X_FORWARDED_FOR, and
	because this sets REMOTE_ADDR based on HTTP_X_FORWARDED_FOR, that means
	anybody can "fake" their IP address. Only use this when you can absolutely
	trust the value of HTTP_X_FORWARDED_FOR.

	The code is from Django 1.0, but removed as unfit for general use.
	"""

	HEADER = "HTTP_X_FORWARDED_FOR"
	# A set of IPs for which the Middleware will trigger.
	# Other IPs will not be replaced.
	INTERNAL_IPS = ("0.0.0.0", "127.0.0.1")

	def process_request(self, request):
		ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
		if ip not in self.INTERNAL_IPS:
			# Do nothing when the IP is considered real
			return

		try:
			real_ip = request.META[self.HEADER]
		except KeyError:
			return
		else:
			# HTTP_X_FORWARDED_FOR can be a comma-separated list of IPs. The
			# client's IP will be the first one.
			real_ip = real_ip.split(",")[0].strip()
			request.META["REMOTE_ADDR"] = real_ip
