from rest_framework import permissions
from .models import APIKey


class APIKeyPermission(permissions.BasePermission):
	"""
	Permission check for presence of an API Key header
	http://www.django-rest-framework.org/api-guide/permissions/
	"""

	HEADER_NAME = "X-Api-Key"

	def has_permission(self, request, view):
		header = "HTTP_" + self.HEADER_NAME.replace("-", "_").upper()
		key = request.META.get(header, "")
		if not key:
			return False

		try:
			api_key = APIKey.objects.get(api_key=key)
		except (APIKey.DoesNotExist, ValueError):
			return False

		request.api_key = api_key
		return api_key.enabled


class IsOwnerOrStaff(permissions.BasePermission):
	"""
	Permission check that only authorizes owners or staff.
	"""

	OWNER_FIELD = "user"

	def has_object_permission(self, request, view, obj):
		if request.user.is_staff:
			return True
		return getattr(obj, self.OWNER_FIELD) == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
	"""
	Permission check that fails on unsafe methods, unless the
	user owns that object.
	"""

	OWNER_FIELD = "user"

	def has_object_permission(self, request, view, obj):
		if request.method in permissions.SAFE_METHODS:
			return True
		return getattr(obj, self.OWNER_FIELD) == request.user
