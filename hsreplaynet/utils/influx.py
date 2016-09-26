"""Utils for interacting with Influx"""
import time
from contextlib import contextmanager
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.timezone import now
from . import log


if settings.INFLUX_ENABLED:
	from influxdb import InfluxDBClient

	dbs = getattr(settings, "INFLUX_DATABASES", None)
	if not dbs or "hsreplaynet" not in dbs:
		raise ImproperlyConfigured('settings.INFLUX_DATABASES["hsreplaynet"] setting is not set')

	influx_settings = settings.INFLUX_DATABASES["hsreplaynet"]

	kwargs = {
		"host": influx_settings["HOST"],
		"port": influx_settings.get("PORT", 8086),
		"username": influx_settings["USER"],
		"password": influx_settings["PASSWORD"],
		"database": influx_settings["NAME"],
		"ssl": influx_settings.get("SSL", False),
		"timeout": influx_settings.get("TIMEOUT", 2)
	}

	udp_port = influx_settings.get("UDP_PORT", 0)
	if udp_port:
		kwargs["use_udp"] = True
		kwargs["udp_port"] = udp_port

	influx = InfluxDBClient(**kwargs)
else:
	influx = None


def influx_write_payload(payload):
	if influx is None:
		return

	try:
		result = influx.write_points(payload)
		if not result:
			log.warn("Influx write failure")
	except Exception as e:
		log.exception("Exception while writing to influx.")
		result = None


def influx_metric(measure, fields, timestamp=None, **kwargs):
	if timestamp is None:
		timestamp = now()

	payload = {
		"measurement": measure,
		"tags": kwargs,
		"fields": fields,
		"time": timestamp.isoformat()
	}
	influx_write_payload([payload])


@contextmanager
def influx_timer(measure, timestamp=None, **kwargs):
	"""
	Reports the duration of the context manager.
	Additional kwargs are passed to InfluxDB as tags.
	"""
	start_time = time.clock()
	exception_raised = False
	if timestamp is None:
		timestamp = now()
	try:
		yield
	except Exception:
		exception_raised = True
		raise
	finally:
		stop_time = time.clock()
		duration = (stop_time - start_time) * 10000

		tags = kwargs
		tags["exception_thrown"] = exception_raised
		payload = {
			"fields": {
				"value": duration,
			},
			"measurement": measure,
			"tags": tags,
			"time": timestamp.isoformat(),
		}

		influx_write_payload([payload])


def get_avg_upload_processing_seconds():
	ms = get_current_lambda_average_duration_millis("process_replay_upload_stream_handler")
	return round(ms / 1000.0, 1)


def get_current_lambda_average_duration_millis(lambda_name, lookback_hours=1):
	metric_name = "%s_duration_ms" % (lambda_name)
	raw_query = """
		select mean(value) from %s
		where exception_thrown = 'False'
		and time > now() - %sh
	"""
	full_query = raw_query % (metric_name, lookback_hours)
	result = influx.query(full_query).raw
	return round(result["series"][0]["values"][0][1])
