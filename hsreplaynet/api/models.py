import uuid
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db import models


class AuthToken(models.Model):
	key = models.UUIDField("Key", primary_key=True)
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
		related_name="auth_tokens", null=True, blank=True
	)
	created = models.DateTimeField("Created", auto_now_add=True)
	creation_apikey = models.ForeignKey("api.APIKey", related_name="tokens")

	test_data = models.BooleanField(default=False)

	def __str__(self):
		return str(self.key)

	def save(self, *args, **kwargs):
		if not self.key:
			self.key = uuid.uuid4()
		return super(AuthToken, self).save(*args, **kwargs)

	@staticmethod
	def get_token_from_header(header):
		header = header.lower()

		method, _, token = header.partition(" ")
		if method != "token":
			return

		try:
			return AuthToken.objects.get(key=token)
		except (AuthToken.DoesNotExist, ValueError):
			pass

	def create_fake_user(self, save=True):
		"""
		Create a User instance with the same username as the key UUID.
		The user has the is_fake attribute set to True.
		"""
		User = get_user_model()
		user = User.objects.create(username=str(self.key), is_fake=True)
		self.user = user
		if save:
			self.save()
		return user


class APIKey(models.Model):
	full_name = models.CharField(max_length=254)
	email = models.EmailField()
	website = models.URLField(blank=True)
	api_key = models.UUIDField(blank=True)
	enabled = models.BooleanField(default=True)

	def __str__(self):
		return self.full_name

	def save(self, *args, **kwargs):
		if not self.api_key:
			self.api_key = uuid.uuid4()
		return super(APIKey, self).save(*args, **kwargs)
