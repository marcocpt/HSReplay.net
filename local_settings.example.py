DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

DEBUG = True
ALLOWED_HOSTS = ["*"]
INTERNAL_IPS = ["127.0.0.1", "::1", "10.0.2.2"]

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"


DATABASES = {
	"default": {
		"ENGINE": "django.db.backends.postgresql",
		"NAME": "hsreplaynet",
		"USER": "postgres",
		"PASSWORD": "",
		"HOST": "",
		"PORT": "",
	}
}


INFLUX_DATABASES = {
	"hsreplaynet": {
		"NAME": "hsreplaynet",
		"HOST": "localhost",
		"PORT": 8086,
		"USER": "",
		"PASSWORD": "",
		"SSL": False,
	},
	"joust": {
		"NAME": "joust",
		"HOST": "localhost",
		"PORT": 8086,
		"USER": "",
		"PASSWORD": "",
		"SSL": False,
	}
}
