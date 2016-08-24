import logging
from django.conf import settings
from hsreplaynet.api.models import APIKey, AuthToken
from hsreplaynet.api.serializers import UploadEventSerializer
from hsreplaynet.uploads.models import UploadEvent, RawUpload,  UploadEventStatus, _generate_upload_key
from hsreplaynet.utils import instrumentation


@instrumentation.lambda_handler(stream_name="replay-upload-processing-stream")
def process_replay_upload_stream_handler(event, context):
	"""
	A handler that consumes records from an AWS Kinesis stream.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_replay_upload_stream_handler")
	kinesis_event = event["Records"][0]["kinesis"]
	raw_upload = RawUpload.from_kinesis_event(kinesis_event)

	existing = UploadEvent.objects.filter(shortid=raw_upload.shortid)
	is_reprocessing = bool(existing)

	logger.info("Processing a RawUpload from Kinesis: %r with is_reprocessing=%s", raw_upload, is_reprocessing)
	process_raw_upload(raw_upload, is_reprocessing)


@instrumentation.lambda_handler(cpu_seconds=180, name="ProcessS3CreateObjectV1")
def process_s3_create_handler(event, context):
	"""
	A handler that is triggered whenever a "..power.log" suffixed object is created in S3.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_s3_create_handler")

	s3_event = event["Records"][0]["s3"]
	raw_upload = RawUpload.from_s3_event(s3_event)
	logger.info("Processing a RawUpload from an S3 event: %r", raw_upload)
	process_raw_upload(raw_upload)


def process_raw_upload(raw_upload, is_reprocessing=False):
	"""Generic processing logic for raw log files."""
	logger = logging.getLogger("hsreplaynet.lambdas.process_raw_upload")

	obj, created = UploadEvent.objects.get_or_create(shortid=raw_upload.shortid)

	if not created and not is_reprocessing:
		logger.info("Invocation is an instance of double_put. Exiting Early.")
		instrumentation.influx_metric("raw_log_double_put", {
			"count": 1,
			"shortid": raw_upload.shortid,
			"key": raw_upload.log_key
		})

		return

	descriptor = raw_upload.descriptor

	new_log_key = _generate_upload_key(raw_upload.timestamp, raw_upload.shortid)
	new_descriptor_key = _generate_upload_key(raw_upload.timestamp, raw_upload.shortid, "descriptor.json")
	new_bucket = settings.AWS_STORAGE_BUCKET_NAME

	raw_upload.prepare_upload_event_log_location(new_bucket, new_log_key, new_descriptor_key)
	upload_metadata = descriptor["upload_metadata"]
	gateway_headers = descriptor["gateway_headers"]

	try:
		header = gateway_headers["Authorization"]
		logger.info("Authorization Header: %s", header)
		token = AuthToken.get_token_from_header(header)

		if not token:
			raise Exception("Malformed or Invalid Authorization Header: %r" % (header))

		obj.token = token
		obj.api_key = APIKey.objects.get(api_key=gateway_headers["X-Api-Key"])
	except Exception as e:
		obj.status = UploadEventStatus.VALIDATION_ERROR
		obj.error = e
		obj.save()
		raise

	obj.file = new_log_key
	obj.descriptor = new_descriptor_key
	obj.upload_ip = descriptor["source_ip"]
	obj.status = UploadEventStatus.VALIDATING

	if obj.token.test_data:
		# For test_data tokens all UploadEvents are test_data = True
		obj.test_data = True

	obj.save()

	# If we get here, now everything is in the DB.
	raw_upload.delete()

	serializer = UploadEventSerializer(obj, data=upload_metadata)
	if serializer.is_valid():
		serializer.save()
		obj.process()
	else:
		obj.error = serializer.errors
		obj.status = UploadEventStatus.VALIDATION_ERROR
		obj.save()


