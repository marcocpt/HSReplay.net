import logging
from django.conf import settings
from hsreplaynet.api.models import APIKey, AuthToken
from hsreplaynet.api.serializers import UploadEventSerializer
from hsreplaynet.uploads.models import (
	UploadEvent, RawUpload, UploadEventStatus, _generate_upload_key
)
from hsreplaynet.utils import instrumentation


@instrumentation.lambda_handler(
	cpu_seconds=180,
	stream_name="replay-upload-processing-stream"
)
def process_replay_upload_stream_handler(event, context):
	"""
	A handler that consumes records from an AWS Kinesis stream.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_replay_upload_stream_handler")
	kinesis_event = event["Records"][0]["kinesis"]
	raw_upload = RawUpload.from_kinesis_event(kinesis_event)

	# Reprocessing will only be True when the UploadEvent was scheduled via the Admin
	reprocessing = raw_upload.attempt_reprocessing

	logger.info(
		"Processing a Kinesis RawUpload: %r (reprocessing=%r)", raw_upload, reprocessing
	)
	process_raw_upload(raw_upload, reprocessing)


@instrumentation.lambda_handler(
	cpu_seconds=180,
	name="ProcessS3CreateObjectV1"
)
def process_s3_create_handler(event, context):
	"""
	A handler that is triggered whenever a "..power.log" suffixed object is created in S3.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_s3_create_handler")

	s3_event = event["Records"][0]["s3"]
	raw_upload = RawUpload.from_s3_event(s3_event)

	# This handler entry point should only fire for new raw log uploads
	reprocessing = False

	logger.info(
		"Processing an S3 RawUpload: %r (reprocessing=%r)", raw_upload, reprocessing
	)
	process_raw_upload(raw_upload, reprocessing)


def process_raw_upload(raw_upload, reprocessing=False):
	"""
	Generic processing logic for raw log files.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_raw_upload")

	obj, created = UploadEvent.objects.get_or_create(shortid=raw_upload.shortid)

	logger.info("The created flag for this upload event is: %r", created)
	if not created and not reprocessing:
		# This can occur two ways:
		# 1) The client sends the PUT request twice
		# 2) Re-enabling processing queues an upload to the stream and the S3 event fires
		logger.info("Invocation is an instance of double_put. Exiting Early.")
		instrumentation.influx_metric("raw_log_double_put", {
			"count": 1,
			"shortid": raw_upload.shortid,
			"key": raw_upload.log_key
		})

		return

	descriptor = raw_upload.descriptor

	new_log_key = _generate_upload_key(raw_upload.timestamp, raw_upload.shortid)

	new_descriptor_key = _generate_upload_key(
		raw_upload.timestamp, raw_upload.shortid, "descriptor.json"
	)
	new_bucket = settings.AWS_STORAGE_BUCKET_NAME

	logger.info("Moving power.log to: %s/%s", new_bucket, new_log_key)
	logger.info("Moving descriptor.json to: %s/%s", new_bucket, new_descriptor_key)

	raw_upload.prepare_upload_event_log_location(
		new_bucket,
		new_log_key,
		new_descriptor_key
	)

	upload_metadata = descriptor["upload_metadata"]
	gateway_headers = descriptor["gateway_headers"]

	if "User-Agent" in gateway_headers:
		logger.info("The uploading user agent is: %s", gateway_headers["User-Agent"])
	else:
		logger.info("A User-Agent header was not provided.")

	obj.file = new_log_key
	obj.descriptor = new_descriptor_key
	obj.upload_ip = descriptor["source_ip"]
	obj.status = UploadEventStatus.VALIDATING
	obj.user_agent = gateway_headers.get("User-Agent", "")[:100]

	try:
		header = gateway_headers["Authorization"]
		token = AuthToken.get_token_from_header(header)

		if not token:
			msg = "Malformed or Invalid Authorization Header: %r" % (header)
			logger.error(msg)
			raise Exception(msg)

		obj.token = token
		obj.api_key = APIKey.objects.get(api_key=gateway_headers["X-Api-Key"])
	except Exception as e:
		logger.error("Exception: %r", e)
		obj.status = UploadEventStatus.VALIDATION_ERROR
		obj.error = e
		obj.save()
		logger.info("All state successfully saved to UploadEvent with id: %r", obj.id)

		# If we get here, now everything is in the DB.
		# Clear out the raw upload so it doesn't clog up the pipeline.
		raw_upload.delete()
		logger.info("Deleting objects from S3 succeeded.")
		logger.info("Validation Error will be raised and we will not proceed to processing")
		raise
	else:
		if "test_data" in upload_metadata or obj.token.test_data:
			logger.info("Upload Event Is TEST DATA")

		if obj.token.test_data:
			# When token.test_data = True, then all UploadEvents are test_data = True
			obj.test_data = True

		obj.save()
		logger.info("All state successfully saved to UploadEvent with id: %r", obj.id)

		# If we get here, now everything is in the DB.
		raw_upload.delete()
		logger.info("Deleting objects from S3 succeeded")

	serializer = UploadEventSerializer(obj, data=upload_metadata)
	if serializer.is_valid():
		logger.info("UploadEvent passed serializer validation")
		serializer.save()

		logger.info("Starting GameReplay processing for UploadEvent")
		obj.process()
	else:
		obj.error = serializer.errors
		logger.info("UploadEvent failed validation with errors: %r", obj.error)

		obj.status = UploadEventStatus.VALIDATION_ERROR
		obj.save()

	logger.info("RawUpload event processing is complete")
