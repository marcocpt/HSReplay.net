from functools import wraps
from django.conf import settings
from django.core.exceptions import PermissionDenied
from .models import Feature


def view_requires_feature_access(feature_name):
	"""A decorator for view objects that enforces the feature access policies."""
	def decorator(view_func):
		@wraps(view_func)
		def wrapper(request, *args, **kwargs):

			if settings.DEBUG:
				# Feature policies are not enforced in development mode
				return view_func(request, *args, **kwargs)

			try:
				feature = Feature.objects.get(name=feature_name)
				is_enabled = feature.enabled_for_user(request.user)
			except Feature.DoesNotExist:
				# Missing features are treated as if they are set to
				# FeatureStatus.STAFF_ONLY. This occurs when new feature code is deployed
				# before the DB is updated
				is_enabled = request.user.is_staff()

			if is_enabled:
				return view_func(request, *args, **kwargs)
			else:
				raise PermissionDenied()

		return wrapper

	return decorator
