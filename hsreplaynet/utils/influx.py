"""Utils for interacting with Influx"""
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


if settings.INFLUX_ENABLED:
	from influxdb import InfluxDBClient

	dbs = getattr(settings, "INFLUX_DATABASES", None)
	if not dbs or "hsreplaynet" not in dbs:
		raise ImproperlyConfigured('settings.INFLUX_DATABASES["hsreplaynet"] setting is not set')

	influx_settings = settings.INFLUX_DATABASES["hsreplaynet"]
	influx = InfluxDBClient(
		host=influx_settings["HOST"],
		port=influx_settings.get("PORT", 8086),
		username=influx_settings["USER"],
		password=influx_settings["PASSWORD"],
		database=influx_settings["NAME"],
		ssl=influx_settings.get("SSL", False),
	)
else:
	influx = None


def get_avg_upload_processing_seconds():
	ms = get_current_lambda_average_duration_millis("process_replay_upload_stream_handler")
	return round(ms / 1000.0, 1)


def get_current_lambda_average_duration_millis(lambda_name, lookback_hours=1):
	metric_name = "%s_duration_ms" % lambda_name
	raw_query = """select mean(value)
					from %s
					where exception_thrown = 'False'
					and time > now() - %sh"""
	full_query = raw_query % (metric_name, lookback_hours)
	result = influx.query(full_query).raw
	return round(result["series"][0]["values"][0][1])
