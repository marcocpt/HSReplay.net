"""
Django settings for hsreplay.net project.
"""

import os
import platform
from django.urls import reverse_lazy


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(BASE_DIR, "build")


ENV_LIVE = platform.node() in ["hsreplay.net", "hearthsim.net"]
ENV_LAMBDA = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
ENV_CI = platform.node() == "build.hearthsim.net"
ENV_PROD = ENV_LIVE or ENV_LAMBDA
ENV_DEV = not ENV_PROD and not ENV_CI

INFLUX_ENABLED = ENV_LIVE or ENV_LAMBDA

if (ENV_DEV or ENV_CI) and (not os.path.exists(BUILD_DIR)):
	os.mkdir(BUILD_DIR)


if ENV_PROD:
	DEBUG = False
	ALLOWED_HOSTS = [".hsreplay.net"]
else:
	# SECURITY WARNING: don't run with debug turned on in production!
	DEBUG = True
	ALLOWED_HOSTS = ["*"]
	INTERNAL_IPS = ["127.0.0.1", "::1"]


ROOT_URLCONF = "hsreplaynet.urls"
WSGI_APPLICATION = "wsgi.application"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "be8^qa&f2fut7_1%q@x2%nkw5u=-r6-rwj8c^+)5m-6e^!zags"


INSTALLED_APPS = [
	"django.contrib.auth",
	"django.contrib.contenttypes",
	"django.contrib.sessions",
	"django.contrib.messages",
	"django.contrib.staticfiles",
	"django.contrib.sites",
	"rest_framework",
	"hsreplaynet.accounts",
	"hsreplaynet.api",
	"hsreplaynet.cards",
	"hsreplaynet.games",
	"hsreplaynet.lambdas",
	"hsreplaynet.scenarios",
	"hsreplaynet.stats",
	"hsreplaynet.uploads",
	"hsreplaynet.utils",
]

if not ENV_LAMBDA:
	INSTALLED_APPS += [
		"django.contrib.admin",
		"django.contrib.flatpages",
		"allauth",
		"allauth.account",
		"allauth.socialaccount",
		"allauth.socialaccount.providers.battlenet",
		"django_rq",
		"django_rq_dashboard",
		"loginas",
		"cloud_browser",
		"webpack_loader",
		"hsreplaynet.admin",
	]

if ENV_PROD:
	INSTALLED_APPS += [
		"raven.contrib.django.raven_compat",
	]


MIDDLEWARE_CLASSES = [
	"django.contrib.sessions.middleware.SessionMiddleware",
	"django.middleware.common.CommonMiddleware",
	"django.middleware.csrf.CsrfViewMiddleware",
	"django.contrib.auth.middleware.AuthenticationMiddleware",
	"django.contrib.messages.middleware.MessageMiddleware",
	"django.middleware.clickjacking.XFrameOptionsMiddleware",
	"django.middleware.security.SecurityMiddleware",
	"django.middleware.gzip.GZipMiddleware",
	"hsreplaynet.utils.middleware.DoNotTrackMiddleware",
]


if ENV_DEV:
	# Django Debug Toolbar
	INSTALLED_APPS += [
		"debug_toolbar",
	]
	MIDDLEWARE_CLASSES += [
		"debug_toolbar.middleware.DebugToolbarMiddleware",
	]
	DEBUG_TOOLBAR_CONFIG = {
		"JQUERY_URL": "",
	}


TEMPLATES = [{
	"BACKEND": "django.template.backends.django.DjangoTemplates",
	"DIRS": [
		os.path.join(BASE_DIR, "hsreplaynet", "templates")
	],
	"APP_DIRS": True,
	"OPTIONS": {
		"context_processors": [
			"django.template.context_processors.debug",
			"django.template.context_processors.request",
			"django.contrib.auth.context_processors.auth",
			"django.contrib.messages.context_processors.messages",
		],
	},
}]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

MEDIA_ROOT = os.path.join(BUILD_DIR, "media")
MEDIA_URL = "/media/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS = [
	os.path.join(BASE_DIR, "hsreplaynet", "static"),
]
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

WEBPACK_LOADER = {
	"DEFAULT": {
		"BUNDLE_DIR_NAME": "bundles/",
		"STATS_FILE": os.path.join(BUILD_DIR, "webpack-stats.json"),
	}
}

DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"
STATIC_URL = "/static/"

if ENV_PROD:
	DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
	STATIC_URL = "https://static.hsreplay.net/static/"

	# S3
	S3_RAW_LOG_STORAGE_BUCKET = os.environ.get(
		"S3_RAW_LOG_STORAGE_BUCKET",
		"hsreplaynet-uploads"
	)
	S3_REPLAY_STORAGE_BUCKET = os.environ.get(
		"S3_REPLAY_STORAGE_BUCKET",
		"hsreplaynet-replays"
	)
	AWS_STORAGE_BUCKET_NAME = S3_REPLAY_STORAGE_BUCKET

	AWS_S3_USE_SSL = True
	AWS_DEFAULT_ACL = "private"

	AWS_IS_GZIPPED = True
	GZIP_CONTENT_TYPES = [
		"text/xml",
		"text/plain",
		"application/xml",
		"application/octet-stream",
	]
else:
	AWS_STORAGE_BUCKET_NAME = "hsreplaynet-dev-replays"

# WARNING: To change this it must also be updated in isolated.uploaders.py
S3_RAW_LOG_UPLOAD_BUCKET = "hsreplaynet-uploads"

KINESIS_UPLOAD_PROCESSING_STREAM_NAME = "replay-upload-processing-stream"
KINESIS_UPLOAD_PROCESSING_STREAM_MIN_SHARDS = 2
KINESIS_UPLOAD_PROCESSING_STREAM_MAX_SHARDS = 32

# The target maximum seconds it should take for kinesis to process a backlog of raw uploads
# This value is used to periodically dynamically resize the stream capacity
KINESIS_STREAM_PROCESSING_THROUGHPUT_SLA_SECONDS = 600


JOUST_STATIC_URL = STATIC_URL + "joust/"
HEARTHSTONEJSON_URL = "https://api.hearthstonejson.com/v1/%(build)s/%(locale)s/cards.json"
HEARTHSTONE_ART_URL = "https://art.hearthstonejson.com/cards/by-id/"

LAMBDA_DEFAULT_EXECUTION_ROLE_NAME = "iam_lambda_execution_role"

# Email
# https://docs.djangoproject.com/en/1.9/ref/settings/#email-backend

SERVER_EMAIL = "admin@hsreplay.net"
DEFAULT_FROM_EMAIL = "contact@hsreplay.net"
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
	"default": {
		"ENGINE": "django.db.backends.sqlite3",
		"NAME": os.path.join(BUILD_DIR, "db.sqlite"),
		"USER": "",
		"PASSWORD": "",
		"HOST": "",
		"PORT": "",
	}
}


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

USE_I18N = False
USE_L10N = True
LANGUAGE_CODE = "en-us"

USE_TZ = True
TIME_ZONE = "UTC"

SITE_ID = 1


# Account settings

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
	# Needed to login by username in Django admin, regardless of `allauth`
	"django.contrib.auth.backends.ModelBackend",
	# `allauth` specific authentication methods, such as login by e-mail
	"allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_REDIRECT_URL = reverse_lazy("my_replays")
LOGIN_URL = reverse_lazy("account_login")

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http" if ENV_DEV else "https"
SOCIALACCOUNT_ADAPTER = "allauth.socialaccount.providers.battlenet.provider.BattleNetSocialAccountAdapter"
SOCIALACCOUNT_PROVIDERS = {"battlenet": {"SCOPE": []}}


# RQ
# https://github.com/ui/django-rq

RQ_QUEUES = {
	"default": {
		"HOST": "localhost",
		"PORT": 6379,
		"DB": 0,
		"PASSWORD": "",
		"DEFAULT_TIMEOUT": 360,
	}
}


# API
REST_FRAMEWORK = {
	# Use Django's standard `django.contrib.auth` permissions,
	# or allow read-only access for unauthenticated users.
	"DEFAULT_PERMISSION_CLASSES": [
		"rest_framework.permissions.IsAuthenticatedOrReadOnly",
	],
	"DEFAULT_PAGINATION_CLASS": "hsreplaynet.api.pagination.DefaultPagination",
}


# Custom site settings

HDT_DOWNLOAD_URL = "https://hsdecktracker.net/download-hsreplay/?utm_source=hsreplay.net&utm_campaign=download"


# Used for compiling SCSS
SCSS_INPUT_FILE = os.path.join(BASE_DIR, "hsreplaynet", "static", "styles", "main.scss")
SCSS_OUTPUT_FILE = SCSS_INPUT_FILE.replace(".scss", ".css")

# Monkeypatch default collectstatic ignore patterns
from django.contrib.staticfiles.apps import StaticFilesConfig
StaticFilesConfig.ignore_patterns += ["*.scss", "*.ts", "*.tsx", "typings.json"]


try:
	from hsreplaynet.local_settings import *
except ImportError as e:
	# Make sure you have a `local_settings.py` file in the same directory as `settings.py`.
	# We raise a verbose error because the file is *required* in production.
	raise RuntimeError("A `local_settings.py` file could not be found or imported. (%s)" % e)


if __name__ == "__main__":
	import json

	print(json.dumps({
		k: v for k, v in globals().items() if (
			k.isupper() and not k.startswith("_") and not k.endswith("_URL")
		)
	}, sort_keys=True, indent="\t"))
