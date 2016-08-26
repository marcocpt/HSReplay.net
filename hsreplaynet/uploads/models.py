from enum import IntEnum
import re
import json
import base64
from datetime import datetime
from django.conf import settings
from django.db import models
from django.dispatch.dispatcher import receiver
from django.urls import reverse
from hsreplaynet.utils.fields import IntEnumField, ShortUUIDField
from hsreplaynet.utils import aws


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
	HAS_UPLOAD_EVENT = 1


class RawUpload(object):
	"""
	Represents a raw upload in S3.
	"""

	RAW_LOG_KEY_PATTERN = r"raw/(?P<ts>[\d/]{16})/(?P<shortid>\w{22})\.power.log"
	HAS_UPLOAD_KEY_PATTERN = r"uploads/(?P<ts>[\d/]{16})/(?P<shortid>\w{22})\.power.log"
	TIMESTAMP_FORMAT = "%Y/%m/%d/%H/%M"

	def __init__(self, bucket, key):
		self.bucket = bucket
		self._log_key = key
		self._upload_event = None

		if key.startswith("raw"):
			self._state = RawUploadState.NEW

			match = re.match(RawUpload.RAW_LOG_KEY_PATTERN, key)
			if not match:
				raise ValueError("Failed to extract shortid and timestamp from key.")

			fields = match.groupdict()
			self._shortid = fields["shortid"]
			self._timestamp = datetime.strptime(fields["ts"], RawUpload.TIMESTAMP_FORMAT)

			self._descriptor_key = self._create_raw_descriptor_key(fields["ts"], fields["shortid"])

		elif key.startswith("uploads"):
			self._state = RawUploadState.HAS_UPLOAD_EVENT

			match = re.match(RawUpload.HAS_UPLOAD_KEY_PATTERN, key)
			if not match:
				raise ValueError("Failed to extract shortid and timestamp from key.")

			fields = match.groupdict()
			self._shortid = fields["shortid"]
			self._timestamp = datetime.strptime(fields["ts"], RawUpload.TIMESTAMP_FORMAT)

			self._upload_event = UploadEvent.objects.get(shortid=self._shortid)
			self._descriptor_key = str(self._upload_event.descriptor)

		else:
			raise NotImplementedError("__init__ is not supported for key pattern: %s" % key)

		self._upload_event_log_bucket = None
		self._upload_event_log_key = None
		self._upload_event_descriptor_key = None
		self._upload_event_location_populated = False

		# These are loaded lazily from S3
		self._descriptor = None

	def __repr__(self):
		return "<RawUpload %s:%s:%s>" % (self.shortid, self.bucket, self.log_key)

	def _create_raw_descriptor_key(self, ts_string, shortid):
		return "raw/%s/%s.descriptor.json" % (ts_string, shortid)

	def prepare_upload_event_log_location(self, bucket, key, descriptor):
		self._upload_event_log_bucket = bucket
		self._upload_event_log_key = key
		self._upload_event_descriptor_key = descriptor

		log_copy_source = "%s/%s" % (self.bucket, self.log_key)
		aws.S3.copy_object(
			Bucket=bucket,
			Key=key,
			CopySource=log_copy_source,
		)

		descriptor_copy_source = "%s/%s" % (self.bucket, self.descriptor_key)
		aws.S3.copy_object(
			Bucket=bucket,
			Key=descriptor,
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
		else:
			raise NotImplementedError("Delete is not supported for state %r" % (self.state))

	@staticmethod
	def from_s3_event(event):
		bucket = event["bucket"]["name"]
		key = event["object"]["key"]

		return RawUpload(bucket, key)

	@staticmethod
	def from_upload_event(event):
		bucket = settings.AWS_STORAGE_BUCKET_NAME
		log_key = str(event.file)

		return RawUpload(bucket, log_key)

	@staticmethod
	def from_kinesis_event(kinesis_event):
		# Kinesis returns the record bytes data base64 encoded
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

	def _get_object(self, key):
		obj = aws.S3.get_object(Bucket=self.bucket, Key=key)
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
		return self.status in (
			UploadEventStatus.UNKNOWN,
			UploadEventStatus.PROCESSING,
			UploadEventStatus.VALIDATING,
		)

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
