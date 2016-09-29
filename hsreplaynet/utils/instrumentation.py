import os
from datetime import datetime, timedelta
from functools import wraps
from django.conf import settings
from django.utils.timezone import now
from raven.contrib.django.raven_compat.models import client as sentry
from hsreplaynet.uploads.models import RawUpload
from . import log
from .influx import influx_timer


def error_handler(e):
	log.exception(e)
	if not settings.ENV_DEV:
		sentry.captureException()


def get_tracing_id(event):
	"""
	Returns the Authorization token as a unique identifier.
	Used in the Lambda logging system to trace sessions.
	"""
	UNKNOWN_ID = "unknown-id"
	records = event["Records"]

	if len(records) > 1:
		# This is a kinesis batch invocation
		return ":".join(r["kinesis"]["partitionKey"] for r in records)

	event_data = records[0]

	if "s3" in event_data:
		# We are in the process_s3_object Lambda
		s3_event = event_data["s3"]
		raw_upload = RawUpload.from_s3_event(s3_event)
		return raw_upload.shortid
	elif "kinesis" in event_data:
		kinesis_event = event_data["kinesis"]
		# We always use the shortid as the partitionKey in kinesis streams
		return kinesis_event["partitionKey"]

	return UNKNOWN_ID


_lambda_descriptors = []


def get_lambda_descriptors():
	return _lambda_descriptors


def build_cloudwatch_url(log_group_name, log_stream_name):
	baseurl = "https://console.aws.amazon.com/cloudwatch/home"
	tpl = "?region=%s#logEventViewer:group=%s;stream=%s;start=%s;end=%s;tz=UTC"
	start = datetime.now()
	end = start + timedelta(days=1)
	return baseurl + tpl % (
		settings.AWS_DEFAULT_REGION,
		log_group_name,
		log_stream_name,
		start.strftime("%Y-%m-%dT%H:%M:%SZ"),
		end.strftime("%Y-%m-%dT%H:%M:%SZ")
	)


def build_admin_url(shortid):
	return "https://dev.hsreplay.net/admin/uploads/uploadevent/?shortid=%s" % (shortid)


def lambda_handler(
	cpu_seconds=60, memory=128, name=None, handler=None,
	stream_name=None, stream_batch_size=1, trap_exceptions=True
):
	"""Indicates the decorated function is a AWS Lambda handler.

	The following standard lifecycle services are provided:
		- Sentry reporting for all Exceptions that propagate
		- Capturing a standard set of metrics for Influx
		- Making sure all connections to the DB are closed
		- Capturing metadata to facilitate deployment

	Args:
	- cpu_seconds - The seconds the function can run before it is terminated. Default: 60
	- memory - The number of MB allocated to the lambda at runtime. Default: 128
	- name - The name for the Lambda on AWS. Default: func.__name__
	- handler - The entry point for the function. Default: handlers.<func.__name__>
	- stream_name - The kinesis stream this lambda will listen on
	- stream_batch_size - How many records per invocation it will consume from kinesis
	- trap_exceptions - Trapping exceptions will prevent Lambda from retrying on failure
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
					context.log_group_name,
					context.log_stream_name
				)
				sentry.user_context({
					"aws_log_group_name": context.log_group_name,
					"aws_log_stream_name": context.log_stream_name,
					"aws_function_name": context.function_name,
					"aws_cloudwatch_url": cloudwatch_url,
					"admin_url": build_admin_url(tracing_id),
					"tracing_id": tracing_id
				})

			try:
				measurement = "%s_duration_ms" % (func.__name__)
				with influx_timer(
					measurement,
					timestamp=now(),
					cloudwatch_url=cloudwatch_url
				):
					return func(event, context)
			except Exception as e:
				log.exception("Got an exception: %r", e)
				if sentry:
					sentry.captureException()
				else:
					log.info("Sentry is not available.")

				if not trap_exceptions:
					raise
			finally:
				from django.db import connection
				connection.close()

		return wrapper

	return inner_lambda_handler
