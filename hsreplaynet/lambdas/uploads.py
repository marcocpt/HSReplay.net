import json
import logging
import base64
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from rest_framework.test import APIRequestFactory
from hsreplaynet.api.views import UploadEventViewSet
from hsreplaynet.uploads.models import (
	UploadEvent, UploadEventType, RawUpload, RawUploadConfigurationError, _generate_upload_key
)
from hsreplaynet.uploads.processing import queue_upload_event_for_processing
from hsreplaynet.utils import instrumentation, aws


def emulate_api_request(method, path, data, headers):
	"""
	Emulates an API request from the API gateway's data.
	"""
	factory = APIRequestFactory()
	method_factory = getattr(factory, method)
	request = method_factory(path, data, **headers)
	SessionMiddleware().process_request(request)
	return request


@instrumentation.lambda_handler(stream_name="replay-upload-processing-stream")
def process_replay_upload_stream_handler(event, context):
	"""
	A handler that consumes records from an AWS Kinesis stream.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_replay_upload_stream_handler")
	logger.info("*** Event Data ***")
	for k,v in event.items():
		logger.info("%s: %s" % (k, v))

	kinesis_event = event["Records"][0]["kinesis"]
	raw_upload = RawUpload.from_kinesis_event(kinesis_event)


	existing = UploadEvent.objects.filter(shortid=raw_upload.shortid)
	is_reprocessing = False

	if existing.count():
		# This will make DRF update the existing UploadEvent
		is_reprocessing = True

	logger.info("Processing a RawUpload from Kinesis: %r with is_reprocessing=%s", raw_upload, is_reprocessing)
	process_raw_upload(raw_upload, is_reprocessing)


@instrumentation.lambda_handler()
def put_s3_create_in_stream_handler(event, context):
	"""
	A handler enqueues RawUploads to kinesis whenever a "..power.log" suffixed object is created in S3.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_s3_create_handler")

	s3_event = event["Records"][0]["s3"]
	raw_upload = RawUpload.from_s3_event(s3_event)
	logger.info("Processing a RawUpload from an S3 event: %r", raw_upload)
	aws.publish_raw_upload_to_processing_stream(raw_upload)



@instrumentation.lambda_handler(cpu_seconds=180, name="ProcessS3CreateObjectV1")
def process_s3_create_handler(event, context):
	"""
	A handler that is triggered whenever a "..power.log" suffixed object is created in S3.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_s3_create_handler")

	s3_event = event["Records"][0]["s3"]
	raw_upload = RawUpload.from_s3_event(s3_event)
	logger.info("Processing a RawUpload from an S3 event: %r", raw_upload)
	try:
		process_raw_upload(raw_upload)
	except RawUploadConfigurationError as e:
		logger.info(str(e))

		# This is thrown when the object is in the failed bucket
		# but the RawUpload gets initialed with a raw/... key
		# This only occurs if this is S3's second attempt to notify lambda
		# We cannot disable the S3 notification retry behavior
		# So we supress this exception as a work around, so we don't get a 3rd attempt.


@instrumentation.lambda_handler(name="ProcessRawUploadSnsHandlerV1")
def process_raw_upload_sns_handler(event, context):
	"""
	A handler that subscribes to an SNS queue to support processing of raw log uploads.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_raw_upload_sns_handler")

	message = json.loads(event["Records"][0]["Sns"]["Message"])
	raw_upload = RawUpload.from_sns_message(message)

	existing = UploadEvent.objects.filter(shortid=raw_upload.shortid)
	is_reprocessing = False

	if existing.count():
		# This will make DRF update the existing UploadEvent
		is_reprocessing = True

	logger.info("Processing a RawUpload from SNS: %r with is_reprocessing=%s", raw_upload, is_reprocessing)
	process_raw_upload(raw_upload, is_reprocessing)


def process_raw_upload(raw_upload, is_reprocessing=False):
	"""A method for processing a raw upload in S3.

	This will usually be invoked by process_s3_create_handler, however
	it can also be invoked when a raw upload is queued for reprocessing via SNS.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_raw_upload")
	logger.info("Processing %r with is_reprocessing=%s", raw_upload, is_reprocessing)

	obj, created = UploadEvent.objects.get_or_create(shortid=raw_upload.shortid, type=1)

	if not created and not is_reprocessing:
		logger.info("Invocation is an instance of double_put. Exiting Early.")
		instrumentation.influx_metric("raw_log_double_put", {
			"count": 1,
			"shortid": raw_upload.shortid,
			"key": raw_upload.log_key
		})

		return

	descriptor = raw_upload.descriptor

	new_key = _generate_upload_key(raw_upload.timestamp, raw_upload.shortid)
	new_bucket = settings.AWS_STORAGE_BUCKET_NAME

	# First we copy the log to the proper location
	logger.info("*** COPY RAW LOG TO NEW LOCATION ***")
	logger.info("SOURCE: %s/%s" % (raw_upload.bucket, raw_upload.log_key))
	logger.info("DESTINATION: %s/%s" % (new_bucket, new_key))

	try:
		raw_upload.prepare_upload_event_log_location(new_bucket, new_key)

		# Then we build the request and send it to DRF
		# If "file" is a string, DRF will interpret as a S3 Key
		upload_metadata = descriptor["upload_metadata"]
		upload_metadata["shortid"] = descriptor["shortid"]
		upload_metadata["file"] = new_key
		upload_metadata["type"] = int(UploadEventType.POWER_LOG)

		gateway_headers = descriptor["gateway_headers"]

		logger.info("Authorization Header: %s" % gateway_headers["Authorization"])

		headers = {
			"HTTP_X_FORWARDED_FOR": descriptor["source_ip"],
			"HTTP_AUTHORIZATION": gateway_headers["Authorization"],
			"HTTP_X_API_KEY": gateway_headers["X-Api-Key"],
			"format": "json",
		}

		path = descriptor["event"]["path"]
		request = emulate_api_request(
			raw_upload.upload_http_method, path, upload_metadata, headers
		)

		result = create_upload_event_from_request(request)
	except Exception as e:
		logger.info("Create Upload Event Failed!!")

		# If DRF fails: delete the copy of the log to not leave orphans around.
		# Then move the failed upload into the failed location for easier inspection.
		raw_upload.make_failed(str(e))
		logger.info("RawUpload has been marked failed: %r", raw_upload)

		raise
	else:
		logger.info("Create Upload Event Success - RawUpload will be deleted.")

		# If DRF returns success, then we delete the raw_upload
		raw_upload.delete()
		# Now we begin the 3rd lambda without the indirection of SNS

		upload = UploadEvent.objects.get(shortid=raw_upload.shortid)
		upload.process()

	logger.info("Processing RawUpload Complete.")
	return result


def create_upload_event_from_request(request):
	logger = logging.getLogger("hsreplaynet.lambdas.create_upload_event_from_request")
	view = UploadEventViewSet.as_view({"post": "create", "put": "update"})

	response = view(request)
	response.render()
	logger.info("Response (code=%r): %s", response.status_code, response.content)

	if response.status_code not in (200, 201):
		# 200 for updated uploads, 201 for created uploads
		result = {
			"result_type": "VALIDATION_ERROR",
			"status_code": response.status_code,
			"body": response.content,
		}
		raise Exception(json.dumps(result))

	# Extract the upload_event from the response and queue it for processing
	upload_event_id = response.data["id"]
	logger.info("Created UploadEvent %r", upload_event_id)
	#queue_upload_event_for_processing(upload_event_id)

	return {
		"result_type": "SUCCESS",
		"body": response.content,
	}


@instrumentation.lambda_handler(cpu_seconds=180, name="ProcessUploadEventV1")
def process_upload_event_handler(event, context):
	"""
	This handler is triggered by SNS whenever someone
	publishes a message to the SNS_PROCESS_UPLOAD_EVENT_TOPIC.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_upload_event_handler")

	message = json.loads(event["Records"][0]["Sns"]["Message"])
	logger.info("SNS message: %r", message)

	# This should never raise DoesNotExist.
	# If it does, the previous lambda made a terrible mistake.
	upload = UploadEvent.objects.get(id=message["id"])
	upload.process()
	
	logger.info("Processing %r (%s)", upload.shortid, upload.status.name)

	logger.info("Status: %s", upload.status.name)
