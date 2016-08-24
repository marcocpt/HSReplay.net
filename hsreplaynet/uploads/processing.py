"""
A module for scheduling UploadEvents to be processed or reprocessed.
"""
import logging
from django.conf import settings
from hsreplaynet.uploads.models import RawUpload
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

	for object in aws.list_all_objects_in(settings.S3_RAW_LOG_UPLOAD_BUCKET, prefix="raw"):
		key = object["Key"]
		if key.endswith("power.log"):  # Don't queue the descriptor files, just the logs.

			raw_upload = RawUpload(settings.S3_RAW_LOG_UPLOAD_BUCKET, key)
			logger.info("About to queue: %s" % str(raw_upload))
			aws.publish_raw_upload_to_processing_stream(raw_upload)


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
			aws.publish_raw_upload_to_processing_stream(raw_upload)


def _requeue_failed_raw_uploads_by_prefix(prefix):
	"""
	Requeue all failed raw logs to attempt processing them into UploadEvents.
	"""
	results = []
	for raw_upload in _list_raw_uploads_by_prefix(prefix):
		result = aws.publish_raw_upload_to_processing_stream(raw_upload)
		results.append(result)

	return results


def queue_upload_event_for_processing(event):
	"""
	This method can be used to requeue UploadEvent's from the Admin panel.
	"""
	if settings.ENV_PROD:
		aws.publish_upload_event_to_processing_stream(event)
	else:
		logger.info("Processing UploadEvent %r locally", event)
		event.process()
