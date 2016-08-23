import json
import os
import time
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.timezone import now
from hsreplaynet.uploads.models import RawUpload
from . import logger


if "raven.contrib.django.raven_compat" in settings.INSTALLED_APPS:
	from raven.contrib.django.raven_compat.models import client as sentry
else:
	sentry = None


def error_handler(e):
	if sentry is not None:
		sentry.captureException()
	else:
		logger.exception(e)


def get_tracing_id(event):
	"""
	Returns the Authorization token as a unique identifier.
	Used in the Lambda logging system to trace sessions.
	"""
	UNKNOWN_ID = "unknown-id"
	event_data = event["Records"][0]

	if "Sns" in event_data:
		# We are in a lambda triggered via SNS
		message = json.loads(event_data["Sns"]["Message"])

		if "shortid" in message:
			# We are in a lambda to process a raw s3 upload
			return message["shortid"]
		elif "token" in message:
			# We are in a lambda for processing an upload event
			return message["token"]
		else:
			return UNKNOWN_ID

	elif "s3" in event_data:
		# We are in the process_s3_object Lambda
		s3_event = event_data['s3']
		raw_upload = RawUpload.from_s3_event(s3_event)
		return raw_upload.shortid

	elif "kinesis" in event_data:
		kinesis_event = event_data['kinesis']
		# We always use the shortid as the partitionKey in kinesis streams
		return kinesis_event["partitionKey"]

	else:

		return UNKNOWN_ID


_lambda_descriptors = []


def get_lambda_descriptors():
	return _lambda_descriptors


def build_cloudwatch_url(log_group_name, log_stream_name):
	baseurl = "https://console.aws.amazon.com/cloudwatch/home"
	tpl = "?region=%s#logEvent:group=%s;stream=%s;start=%s"
	return baseurl + tpl % (
		settings.AWS_DEFAULT_REGION,
		log_group_name,
		log_stream_name,
		datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
	)


def build_papertrail_url(tracing_id):
	return "https://papertrailapp.com/systems/Lambda/events?q=%s" % tracing_id


def lambda_handler(cpu_seconds=60, memory=128, name=None, handler=None, stream_name=None, stream_batch_size=1):
	"""Indicates the decorated function is a AWS Lambda handler.

	The following standard lifecycle services are provided:
		- Sentry reporting for all Exceptions that propagate
		- Capturing a standard set of metrics for Influx
		- Making sure all connections to the DB are closed
		- Capturing metadata to facilicate deployment

	Args:
	- cpu_seconds - The seconds the function can run before it is terminated. Default: 60
	- memory - The number of MB allocated to the lambda at runtime. Default: 128
	- name - The name for the Lambda on AWS. Default: func.__name__
	- handler - The entry point for the function. Default: handlers.<func.__name__>
	"""

	def inner_lambda_handler(func):

		global _lambda_descriptors

		_lambda_descriptors.append({
			"memory": memory,
			"cpu_seconds": cpu_seconds,
			"name": name if name else func.__name__,
			"handler": handler if handler else "handlers.%s" % func.__name__,
			"stream_name": stream_name if stream_name else None,
			"stream_batch_size": stream_batch_size
		})

		@wraps(func)
		def wrapper(event, context):
			tracing_id = get_tracing_id(event)
			os.environ["TRACING_REQUEST_ID"] = tracing_id
			if sentry:
				# Provide additional metadata to sentry in case the exception
				# gets trapped and reported within the function.
				cloudwatch_url = build_cloudwatch_url(
					context.log_group_name, context.log_stream_name
				)
				sentry.user_context({
					"aws_log_group_name": context.log_group_name,
					"aws_log_stream_name": context.log_stream_name,
					"aws_function_name": context.function_name,
					"aws_cloudwatch_url": cloudwatch_url,
					"papertrail_url": build_papertrail_url(tracing_id),
					"tracing_id": tracing_id
				})

			try:
				measurement = "%s_duration_ms" % (func.__name__)
				with influx_timer(measurement, timestamp=now()):
					return func(event, context)
			except Exception as e:
				logger.exception("Got an exception: %r", e)
				if sentry:
					logger.info("Inside sentry capture block.")
					sentry.captureException()
				else:
					logger.info("Sentry is not available.")
				raise
			finally:
				from django.db import connection
				connection.close()

		return wrapper

	return inner_lambda_handler


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


def influx_write_payload(payload):
	try:
		result = influx.write_points(payload)
		if not result:
			logger.warn("Influx Write Failure.")
	except Exception as e:
		# Can happen if Influx if not available for example
		error_handler(e)


def influx_metric(measure, fields, timestamp=None, **kwargs):
	if influx is None:
		return

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

		if influx:
			influx_write_payload([payload])
