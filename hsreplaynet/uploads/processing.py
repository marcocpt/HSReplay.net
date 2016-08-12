"""
A module for scheduling UploadEvents to be processed or reprocessed.

For additional details see:
http://boto3.readthedocs.io/en/latest/reference/services/sns.html#SNS.Client.publish
"""
import logging
import os
from django.conf import settings
from django.utils.timezone import now
from hsreplaynet.uploads.models import UploadEvent, RawUpload
from hsreplaynet.utils.instrumentation import error_handler, influx_metric
from hsreplaynet.utils import aws

logger = logging.getLogger(__file__)


def queue_raw_uploads_for_processing():
	"""
	Queue all raw logs to attempt processing them into UploadEvents.

	The primary use for this is for when we deploy code. The intended deploy process is:
		- Notify S3 to suspend triggering lambda upon log upload
		- Perform the Deploy
		- Notify S3 to resume triggering lambda upon log upload
		- Invoke this function to queue for processing any logs uploaded during the deploy

	This method is not intended to requeue uploads that have previously failed.
	For that see the requeue_failed_* family of methods.
	"""

	logger.info("Starting - Queue all raw uploads for processing")

	topic_arn = aws.get_sns_topic_arn_from_name(settings.SNS_PROCESS_RAW_LOG_UPOAD_TOPIC)

	if topic_arn is None:
		raise Exception("A Topic for queueing raw uploads is not configured.")

	for object in aws.list_all_objects_in(settings.S3_RAW_LOG_UPLOAD_BUCKET, prefix="raw"):
		key = object["Key"]
		if key.endswith("power.log"):  # Don't queue the descriptor files, just the logs.

			raw_upload = RawUpload(settings.S3_RAW_LOG_UPLOAD_BUCKET, key)
			logger.info("About to queue: %s" % str(raw_upload))

			aws.publish_sns_message(topic_arn, raw_upload.sns_message)


def check_for_failed_raw_upload_with_id(shortid):
	"""
	Will return any error data provided by DRF when a raw upload fails processing.

	This method can be used to embed error info for admins on replay detail pages.

	Args:
		shortid - The shortid to check for an error.
	"""
	prefix = "failed/%s" % shortid
	matching_uploads = list(_list_raw_uploads_by_prefix(prefix))
	if len(matching_uploads) > 0:
		return matching_uploads[0]
	else:
		return None


def _list_raw_uploads_by_prefix(prefix):
	for object in aws.list_all_objects_in(settings.S3_RAW_LOG_UPLOAD_BUCKET, prefix=prefix):
		key = object["Key"]
		if key.endswith("power.log"):  # Just emit one message per power.log
			yield RawUpload(settings.S3_RAW_LOG_UPLOAD_BUCKET, key)


def requeue_failed_raw_uploads_all():
	"""
	Requeue all failed raw logs to attempt processing them into UploadEvents.
	"""
	return _requeue_failed_raw_uploads_by_prefix("failed")


def requeue_failed_raw_logs_uploaded_after(cutoff):
	"""
	Requeue all failed raw logs that were uploaded more recently than the provided timestamp.

	Args:
	- cutoff - Will requeue failed uploads more recent than this datetime
	"""
	prefix = "failed"
	for raw_upload in _list_raw_uploads_by_prefix(prefix):
		if raw_upload.timestamp >= cutoff:
			_publish_requeue_message_for_failed_raw_log(raw_upload)


def _requeue_failed_raw_uploads_by_prefix(prefix):
	"""
	Requeue all failed raw logs to attempt processing them into UploadEvents.
	"""
	results = []
	for raw_upload in _list_raw_uploads_by_prefix(prefix):
		result = _publish_requeue_message_for_failed_raw_log(raw_upload)
		results.append(result)

	return results


def _publish_requeue_message_for_failed_raw_log(raw_upload):

	topic_arn = aws.get_sns_topic_arn_from_name(settings.SNS_PROCESS_RAW_LOG_UPOAD_TOPIC)

	if topic_arn is None:
		raise Exception("A Topic for queueing raw uploads is not configured.")

	return aws.publish_sns_message(topic_arn, raw_upload.sns_message)


def queue_upload_event_for_processing(upload_event_id):
	"""
	This method is used when UploadEvents are initially created.
	However it can also be used to requeue an UploadEvent to be
	processed again if an error was detected downstream that has now been fixed.
	"""
	if settings.ENV_PROD:
		if "TRACING_REQUEST_ID" in os.environ:
			token = os.environ["TRACING_REQUEST_ID"]
		else:
			# If this was re-queued manually the tracing ID may not be set yet.
			event = UploadEvent.objects.get(id=upload_event_id)
			token = str(event.shortid)

		message = {
			"id": upload_event_id,
			"token": token
		}

		success = True
		try:
			logger.info("Submitting %r to SNS", message)
			sns_topic_arn = aws.get_sns_topic_arn_from_name(settings.SNS_PROCESS_UPLOAD_EVENT_TOPIC)
			response = aws.publish_sns_message(sns_topic_arn, message)
			logger.info("SNS Response: %s" % str(response))
		except Exception as e:
			logger.error("Exception raised.")
			error_handler(e)
			success = False
		finally:
			influx_metric(
				"queue_upload_event_for_processing",
				fields={"value": 1},
				timestamp=now(),
				tags={
					"success": success,
					"is_running_as_lambda": settings.ENV_LAMBDA,
				}
			)
	else:
		logger.info("Processing UploadEvent %r locally", upload_event_id)
		upload = UploadEvent.objects.get(id=upload_event_id)
		upload.process()
