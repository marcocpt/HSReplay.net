#!/usr/bin/env python
"""
Initialize a database with the following:

- An admin user, with the password 'admin'
- A non-admin user, with the password 'user'
- The default site set to localhost:8000

"""

import os; os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hsreplaynet.settings")
import sys; sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import django; django.setup()
from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.auth import get_user_model
from django.contrib.flatpages.models import FlatPage
from hsreplaynet.api.models import APIKey, AuthToken


User = get_user_model()
API_KEY_NAME = "HSReplay.net Development Key"


def create_or_update_user(username, password, apikey, admin=False):
	user, created = User.objects.get_or_create(username=username)
	user.is_superuser = admin
	user.is_staff = admin
	user.set_password(password)
	user.email = username + "@localhost"
	user.save()

	# Associate an auth token with the user
	token, created = AuthToken.objects.get_or_create(
		user=user, creation_apikey=apikey,
	)

	return user, token


def update_default_site(site_id):
	site = Site.objects.get(id=site_id)
	site.name = "HSReplay.net (development)"
	site.domain = "localhost:8000"
	site.save()
	return site


def create_default_api_key():
	key, created = APIKey.objects.get_or_create(full_name=API_KEY_NAME)
	key.email = "admin@localhost"
	key.website = "http://localhost:8000"
	key.save()
	return key


def create_default_flatpage(url, title):
	page, created = FlatPage.objects.get_or_create(url=url, title=title)
	if not page.sites.count():
		page.sites.add(settings.SITE_ID)
	return page


def main():
	update_default_site(settings.SITE_ID)
	apikey = create_default_api_key()
	create_or_update_user("admin", "admin", apikey, admin=True)
	create_or_update_user("user", "user", apikey)
	create_default_flatpage("/about/privacy/", "Privacy Policy")
	create_default_flatpage("/about/tos/", "Terms of Service")


if __name__ == "__main__":
	main()
