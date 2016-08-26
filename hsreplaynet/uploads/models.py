from enum import IntEnum
import re
import json
import base64
from datetime import datetime
from django.conf import settings
from django.db import models
from django.dispatch.dispatcher import receiver
from django.utils.timezone import now
from django.urls import reverse
from hsreplaynet.utils.fields import IntEnumField, ShortUUIDField
from hsreplaynet.utils import aws

try:
	from botocore.exceptions import ClientError
except ImportError:
	pass


class UploadEventStatus(IntEnum):
	UNKNOWN = 0
	PROCESSING = 1
	SERVER_ERROR = 2
	PARSING_ERROR = 3
	SUCCESS = 4
	UNSUPPORTED = 5
	VALIDATION_ERROR = 6
	VALIDATING = 7


class RawUploadState(IntEnum):
	NEW = 0
	FAILED = 1


class RawUploadConfigurationError(Exception):
	pass


class RawUpload(object):
	"""
	Represents a raw upload in S3.
	"""

	RAW_LOG_KEY_PATTERN = r"raw/(?P<ts>[\d/]{16})/(?P<shortid>\w{22})\.power.log"
	RAW_TIMESTAMP_FORMAT = "%Y/%m/%d/%H/%M"

	FAILED_LOG_KEY_PATTERN = r"failed/(?P<shortid>\w{22})/(?P<ts>[\d-]+)\.power.log"
	FAILED_TIMESTAMP_FORMAT = "%Y-%m-%d-%H-%M"

	def __init__(self, bucket, key):
		self.bucket = bucket
		self._log_key = key

		if key.startswith("raw"):
			self._state = RawUploadState.NEW

			match = re.match(RawUpload.RAW_LOG_KEY_PATTERN, key)
			if not match:
				raise ValueError("Failed to extract shortid and timestamp from key.")

			fields = match.groupdict()
			self._shortid = fields["shortid"]
			self._timestamp = datetime.strptime(fields["ts"], RawUpload.RAW_TIMESTAMP_FORMAT)

			self._descriptor_key = self._create_raw_descriptor_key(fields["ts"], fields["shortid"])
			self._error_key = None  # New RawUploads should never have an error object

		elif key.startswith("failed"):
			self._state = RawUploadState.FAILED

			match = re.match(RawUpload.FAILED_LOG_KEY_PATTERN, key)
			if not match:
				raise ValueError("Failed to extract shortid and timestamp from key.")

			fields = match.groupdict()
			self._shortid = fields["shortid"]
			self._timestamp = datetime.strptime(fields["ts"], RawUpload.FAILED_TIMESTAMP_FORMAT)

			self._descriptor_key = self._create_failed_descriptor_key(
				fields["ts"], fields["shortid"],
			)
			self._error_key = self._create_failed_error_key(fields["ts"], fields["shortid"])

		else:
			raise NotImplementedError("__init__ is not supported for key pattern: %s" % key)

		self._upload_event_log_bucket = None
		self._upload_event_log_key = None
		self._upload_event_location_populated = False

		# These are loaded lazily from S3
		self._descriptor = None
		self._error = None

		# Always use "put" by default.
		# If you use "post" a new UploadEvent will be created
		self.upload_http_method = "put"

	def __repr__(self):
		return "<RawUpload %s:%s:%s>" % (self.shortid, self.bucket, self.log_key)

	def _create_raw_descriptor_key(self, ts_string, shortid):
		return "raw/%s/%s.descriptor.json" % (ts_string, shortid)

	def _create_failed_descriptor_key(self, ts_string, shortid):
		return "failed/%s/%s.descriptor.json" % (shortid, ts_string)

	def _create_failed_error_key(self, ts_string, shortid):
		return "failed/%s/%s.error.json" % (shortid, ts_string)

	def _create_failed_log_key(self, ts_string, shortid):
		return "failed/%s/%s.power.log" % (shortid, ts_string)

	@property
	def is_present_in_failed_bucket(self):
		ts_string = self.timestamp.strftime(RawUpload.FAILED_TIMESTAMP_FORMAT)
		try:
			obj = aws.S3.head_object(
				Bucket=self.bucket,
				Key=self._create_failed_log_key(ts_string, self.shortid)
			)
		except Exception:
			return False
		else:
			return True

	def make_failed(self, reason):
		if self._upload_event_location_populated:
			# TODO: Do we need to revert the descriptor.json

			# Always revert our temporary copy of the log to the uploads location
			aws.S3.delete_object(
				Bucket=self._upload_event_log_bucket,
				Key=self._upload_event_log_key
			)

			self._upload_event_location_populated = False

		ts_string = self.timestamp.strftime(RawUpload.FAILED_TIMESTAMP_FORMAT)

		if self._state == RawUploadState.FAILED:
			# This RawUpload started out in the /failed directory,
			# so there is no need to move things there.
			# However, we do still need to update the error message
			# in casethe failure was for a different reason.
			self._create_or_update_error_messages(reason, ts_string)
		else:

			failed_log_key = self._create_failed_log_key(ts_string, self.shortid)
			failed_log_copy_source = "%s/%s" % (self.bucket, self.log_key)
			aws.S3.copy_object(
				Bucket=self.bucket,
				Key=failed_log_key,
				CopySource=failed_log_copy_source,
			)

			failed_descriptor_key = self._create_failed_descriptor_key(ts_string, self.shortid)
			failed_descriptor_copy_source = "%s/%s" % (self.bucket, self.descriptor_key)
			aws.S3.copy_object(
				Bucket=self.bucket,
				Key=failed_descriptor_key,
				CopySource=failed_descriptor_copy_source,
			)

			self._create_or_update_error_messages(reason, ts_string)

			# Finally remove the two objects from the /raw prefix to avoid that filling up.
			aws.S3.delete_objects(
				Bucket=self.bucket,
				Delete={
					"Objects": [{"Key": self.log_key}, {"Key": self.descriptor_key}]
				}
			)

			self._log_key = failed_log_key
			self._descriptor_key = failed_descriptor_key
			self._state = RawUploadState.FAILED

	def _create_or_update_error_messages(self, reason, ts_string):
		# If the upload failed previously retrieve the history of errors to append to it.
		if self._state == RawUploadState.FAILED:
			error_json = self.error
		else:
			error_json = {"attempts": []}

		try:
			current_attempt_json = json.loads(reason)
		except Exception:
			current_attempt_json = {"reason": reason}

		current_attempt_json["failure_ts"] = now().isoformat()

		error_json["attempts"].append(current_attempt_json)

		failed_error_key = self._create_failed_error_key(ts_string, self.shortid)
		aws.S3.put_object(
			Key=failed_error_key,
			Body=json.dumps(error_json, sort_keys=True, indent=4).encode("utf8"),
			Bucket=self.bucket,
		)

		self._error_key = failed_error_key

	def prepare_upload_event_log_location(self, upload_event_bucket, upload_event_key, upload_event_descriptor):
		self._upload_event_log_bucket = upload_event_bucket
		self._upload_event_log_key = upload_event_key

		log_copy_source = "%s/%s" % (self.bucket, self.log_key)
		aws.S3.copy_object(
			Bucket=upload_event_bucket,
			Key=upload_event_key,
			CopySource=log_copy_source,
		)

		descriptor_copy_source = "%s/%s" % (self.bucket, self.descriptor_key)
		aws.S3.copy_object(
			Bucket=upload_event_bucket,
			Key=upload_event_descriptor,
			CopySource=descriptor_copy_source,
		)

		self._upload_event_location_populated = True

	def delete(self):
		if self.state == RawUploadState.NEW:
			aws.S3.delete_objects(
				Bucket=self.bucket,
				Delete={
					"Objects": [{"Key": self.log_key}, {"Key": self.descriptor_key}]
				}
			)
		elif self.state == RawUploadState.FAILED:
			aws.S3.delete_objects(
				Bucket=self.bucket,
				Delete={
					"Objects": [
						{"Key": self.log_key},
						{"Key": self.descriptor_key},
						{"Key": self.error_key}
					]
				}
			)
		else:
			raise NotImplementedError("Delete is not supported for state: %s" % self.state.name)

	@staticmethod
	def from_s3_event(event):
		bucket = event["bucket"]["name"]
		key = event["object"]["key"]

		return RawUpload(bucket, key)

	@staticmethod
	def from_kinesis_event(kinesis_event):
		#Kinesis returns the record bytes data base64 encoded
		payload = base64.b64decode(kinesis_event["data"])
		json_str = payload.decode("utf8")
		data = json.loads(json_str)

		return RawUpload(data["bucket"], data["log_key"])

	@property
	def kinesis_data(self):
		data = {
				"bucket": self.bucket,
				"log_key": self.log_key,
		}
		json_str = json.dumps(data)
		payload = json_str.encode("utf8")
		# Kinesis will base64 encode the payload bytes for us.
		# However, when we read the record back we will have to decode from base64 ourselves
		return payload

	@property
	def kinesis_partition_key(self):
		# The partition key is also used as the tracing ID
		return self.shortid

	@property
	def state(self):
		return self._state

	@property
	def log_key(self):
		return self._log_key

	@property
	def log_url(self):
		return self._signed_url_for(self._log_key)

	@property
	def descriptor_key(self):
		return self._descriptor_key

	@property
	def descriptor_url(self):
		return self._signed_url_for(self._descriptor_key)

	@property
	def descriptor(self):
		if self._descriptor is None:
			self._descriptor = self._get_object(self._descriptor_key)

		return self._descriptor

	@property
	def error_key(self):
		return self._error_key

	@property
	def error(self):
		if self._error is None:
			self._error = self._get_object(self._error_key)

		return self._error

	@property
	def error_str(self):
		return json.dumps(self.error, sort_keys=True, indent=4)

	@property
	def error_url(self):
		return self._signed_url_for(self._error_key)

	def _get_object(self, key):
		try:
			obj = aws.S3.get_object(Bucket=self.bucket, Key=key)
		except ClientError:
			is_new_upload = self.state == RawUploadState.NEW
			is_in_failed = self.is_present_in_failed_bucket

			if is_new_upload and is_in_failed:
				msg = "The RawUpload was initialed as NEW but is actually located in /failed"
				raise RawUploadConfigurationError(msg)
			else:
				raise
		else:
			return json.loads(obj["Body"].read().decode("utf8"))

	def _signed_url_for(self, key):
		return aws.S3.generate_presigned_url(
			"get_object",
			Params={
				"Bucket": self.bucket,
				"Key": key
			},
			ExpiresIn=60 * 60 * 24,
			HttpMethod="GET"
		)

	@property
	def shortid(self):
		return self._shortid

	@property
	def timestamp(self):
		return self._timestamp


def _generate_upload_path(instance, filename):
	return _generate_upload_key(instance.created, instance.shortid, "power.log")


def _generate_descriptor_path(instance, filename):
	return _generate_upload_key(instance.created, instance.shortid, "descriptor.json")


def _generate_upload_key(ts, shortid, suffix="power.log"):
	timestamp = ts.strftime("%Y/%m/%d/%H/%M")
	return "uploads/%s/%s.%s" % (timestamp, shortid, suffix)


class UploadEvent(models.Model):
	"""
	Represents a game upload, before the creation of the game itself.

	The metadata captured is what was provided by the uploader.
	The raw logs have not yet been parsed for validity.
	"""
	id = models.BigAutoField(primary_key=True)
	shortid = ShortUUIDField("Short ID")
	token = models.ForeignKey(
		"api.AuthToken", on_delete=models.CASCADE,
		null=True, blank=True, related_name="uploads"
	)
	api_key = models.ForeignKey(
		"api.APIKey", on_delete=models.SET_NULL,
		null=True, blank=True, related_name="uploads"
	)
	game = models.ForeignKey(
		"games.GameReplay", on_delete=models.SET_NULL,
		null=True, blank=True, related_name="uploads"
	)
	created = models.DateTimeField(auto_now_add=True)
	upload_ip = models.GenericIPAddressField(null=True)
	status = IntEnumField(enum=UploadEventStatus, default=UploadEventStatus.UNKNOWN)
	tainted = models.BooleanField(default=False)
	error = models.TextField(blank=True)
	traceback = models.TextField(blank=True)
	test_data = models.BooleanField(default=False)

	metadata = models.TextField(blank=True)
	file = models.FileField(upload_to=_generate_upload_path, null=True)
	descriptor = models.FileField(upload_to=_generate_descriptor_path, null=True)
	attempts = models.TextField(blank=True)

	def __str__(self):
		return self.shortid

	@property
	def is_processing(self):
		return self.status in (UploadEventStatus.UNKNOWN, UploadEventStatus.PROCESSING)

	def get_absolute_url(self):
		return reverse("upload_detail", kwargs={"shortid": self.shortid})

	def process(self):
		from hsreplaynet.games.processing import process_upload_event

		process_upload_event(self)


@receiver(models.signals.post_delete, sender=UploadEvent)
def cleanup_uploaded_log_file(sender, instance, **kwargs):
	from hsreplaynet.utils import delete_file_async

	file = instance.file
	if file.name:
		delete_file_async(file.name)
