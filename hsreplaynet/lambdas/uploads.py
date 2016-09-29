import logging
import json
from threading import Thread
from django.conf import settings
from hsreplaynet.api.models import APIKey, AuthToken
from hsreplaynet.api.serializers import UploadEventSerializer
from hsreplaynet.uploads.models import (
	UploadEvent, RawUpload, UploadEventStatus, _generate_upload_key
)
from hsreplaynet.utils import instrumentation
from hsreplaynet.utils.aws.clients import LAMBDA
from hsreplaynet.utils.latch import CountDownLatch
from hsreplaynet.utils.influx import influx_metric


@instrumentation.lambda_handler(
	cpu_seconds=180,
	stream_name="replay-upload-processing-stream",
	stream_batch_size=256
)
def process_replay_upload_stream_handler(event, context):
	"""
	A handler that supports reading from a stream with batch size > 1.

	If this handler is invoked with N records in the event, then it will invoke the
	single record processing lambda N times in parallel and exit once they have
	all returned.

	In combination with the number of shards in the stream, this allows for tuning the
	parallelism of processing a stream more dynamically. The parallelism of the stream
	is governed by:

	CONCURRENT_LAMBDAS = NUM_SHARDS * STREAM_BATCH_SIZE

	This also provides for controllable concurrency of lambdas much more cost efficiently
	as we can run with many fewer shards, and we only pay the tax of this additional
	lambda invocation. For example, with stream_batch_size = 2, this costs 50% as much
	as adding a second shard would cost. With stream_batch_size = 8, this costs 7% as
	much as adding 7 additional shards would cost.

	When using this lambda, the number of shards should be set to be the fewest number
	required to achieve the required write throughput. Then the batch size of this lambda
	should be tuned to achieve the final desired concurrency level.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_replay_upload_stream_handler")
	records = event["Records"]
	num_records = len(records)
	logger.info("Kinesis batch handler invoked with %s records", num_records)

	countdown_latch = CountDownLatch(num_records)

	def lambda_invoker(payload, shortid):
		try:
			LAMBDA.invoke(
				FunctionName="process_single_replay_upload_stream_handler",
				InvocationType="RequestResponse",  # Triggers synchronous invocation
				Payload=payload,
			)
		finally:
			logger.info("Lambda completed for %s Decrementing latch.", shortid)
			countdown_latch.count_down()

	for record in records:
		shortid = record["kinesis"]["partitionKey"]
		payload = json.dumps({"Records": [record]})
		logger.info("Invoking Lambda for %s", shortid)
		lambda_invocation = Thread(target=lambda_invoker, args=(payload, shortid))
		lambda_invocation.start()

	# We will exit once all child invocations have returned.
	countdown_latch.await()
	logger.info("All child invocations have completed")


@instrumentation.lambda_handler(cpu_seconds=180)
def process_single_replay_upload_stream_handler(event, context):
	"""
	A handler that consumes single records from an AWS Kinesis stream.
	"""
	logger = logging.getLogger(
		"hsreplaynet.lambdas.process_single_replay_upload_stream_handler"
	)
	log_group_name = context.log_group_name
	log_stream_name = context.log_stream_name

	kinesis_event = event["Records"][0]["kinesis"]
	raw_upload = RawUpload.from_kinesis_event(kinesis_event)

	# Reprocessing will only be True when the UploadEvent was scheduled via the Admin
	reprocessing = raw_upload.attempt_reprocessing

	logger.info(
		"Processing a Kinesis RawUpload: %r (reprocessing=%r)", raw_upload, reprocessing
	)
	process_raw_upload(raw_upload, reprocessing, log_group_name, log_stream_name)


@instrumentation.lambda_handler(
	cpu_seconds=180,
	name="ProcessS3CreateObjectV1"
)
def process_s3_create_handler(event, context):
	"""
	A handler that is triggered whenever a "..power.log" suffixed object is created in S3.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_s3_create_handler")
	log_group_name = context.log_group_name
	log_stream_name = context.log_stream_name

	s3_event = event["Records"][0]["s3"]
	raw_upload = RawUpload.from_s3_event(s3_event)

	# This handler entry point should only fire for new raw log uploads
	reprocessing = False

	logger.info(
		"Processing an S3 RawUpload: %r (reprocessing=%r)", raw_upload, reprocessing
	)
	process_raw_upload(raw_upload, reprocessing, log_group_name, log_stream_name)


def process_raw_upload(raw_upload, reprocess=False, log_group_name="", log_stream_name=""):
	"""
	Generic processing logic for raw log files.
	"""
	logger = logging.getLogger("hsreplaynet.lambdas.process_raw_upload")

	obj, created = UploadEvent.objects.get_or_create(
		shortid=raw_upload.shortid,
		defaults={"status": UploadEventStatus.PENDING}
	)

	logger.info("The created flag for this upload event is: %r", created)
	if not created and not reprocess:
		# This can occur two ways:
		# 1) The client sends the PUT request twice
		# 2) Re-enabling processing queues an upload to the stream and the S3 event fires
		logger.info("Invocation is an instance of double_put. Exiting Early.")
		influx_metric("raw_log_double_put", {
			"count": 1,
			"shortid": raw_upload.shortid,
			"key": raw_upload.log_key
		})

		return

	obj.log_stream_name = log_group_name
	obj.log_stream_name = log_stream_name

	descriptor = raw_upload.descriptor

	new_log_key = _generate_upload_key(raw_upload.timestamp, raw_upload.shortid)

	new_descriptor_key = _generate_upload_key(
		raw_upload.timestamp, raw_upload.shortid, "descriptor.json"
	)
	new_bucket = settings.AWS_STORAGE_BUCKET_NAME

	# Move power.log/descriptor.json to the other bucket if it's needed
	raw_upload.prepare_upload_event_log_location(new_bucket, new_log_key, new_descriptor_key)

	upload_metadata = descriptor["upload_metadata"]
	gateway_headers = descriptor["gateway_headers"]

	if "User-Agent" in gateway_headers:
		logger.info("The uploading user agent is: %s", gateway_headers["User-Agent"])
	else:
		logger.info("A User-Agent header was not provided.")

	obj.file = new_log_key
	obj.descriptor = new_descriptor_key
	obj.upload_ip = descriptor["source_ip"]
	obj.canary = "canary" in upload_metadata and upload_metadata["canary"]
	obj.user_agent = gateway_headers.get("User-Agent", "")[:100]
	obj.status = UploadEventStatus.VALIDATING

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

		# Only old clients released during beta do not include a user agent
		is_unsupported_client = not obj.user_agent
		if is_unsupported_client:
			logger.info("No UA provided. Marking as unsupported (client too old).")
			influx_metric("upload_from_unsupported_client", {
				"count": 1,
				"shortid": raw_upload.shortid,
				"api_key": obj.api_key.full_name
			})
			obj.status = UploadEventStatus.UNSUPPORTED_CLIENT

		obj.save()
		logger.info("All state successfully saved to UploadEvent with id: %r", obj.id)

		# If we get here, now everything is in the DB.
		raw_upload.delete()
		logger.info("Deleting objects from S3 succeeded")

		if is_unsupported_client:
			# Wait until after we have deleted the raw_upload to exit
			# But do not start processing if it's an unsupported client
			logger.info("Exiting Without Processing - Unsupported Client")
			return

	serializer = UploadEventSerializer(obj, data=upload_metadata)
	if serializer.is_valid():
		logger.info("UploadEvent passed serializer validation")
		obj.status = UploadEventStatus.PROCESSING
		serializer.save()

		logger.info("Starting GameReplay processing for UploadEvent")
		obj.process()
	else:
		obj.error = serializer.errors
		logger.info("UploadEvent failed validation with errors: %r", obj.error)

		obj.status = UploadEventStatus.VALIDATION_ERROR
		obj.save()

	logger.info("RawUpload event processing is complete")
