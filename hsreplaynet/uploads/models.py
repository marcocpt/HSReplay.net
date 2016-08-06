from enum import IntEnum
import re
import json
from datetime import datetime
from django.core.files.storage import default_storage
from django.db import models
from django.dispatch.dispatcher import receiver
from django.utils.timezone import now
from django.urls import reverse
from hsreplaynet.utils.fields import IntEnumField, ShortUUIDField
from hsreplaynet.utils import aws


class UploadEventType(IntEnum):
	POWER_LOG = 1
	OUTPUT_TXT = 2
	HSREPLAY_XML = 3

	@property
	def extension(self):
		if self.name == "POWER_LOG":
			return ".power.log"
		elif self.name == "OUTPUT_TXT":
			return ".output.txt"
		elif self.name == "HSREPLAY_XML":
			return ".hsreplay.xml"
		return ".txt"


class UploadEventStatus(IntEnum):
	UNKNOWN = 0
	PROCESSING = 1
	SERVER_ERROR = 2
	PARSING_ERROR = 3
	SUCCESS = 4
	UNSUPPORTED = 5
	VALIDATION_ERROR = 6


class RawUploadState(IntEnum):
	NEW = 0
	FAILED = 1


class RawUpload(object):
	"""Represents a raw upload in S3."""

	RAW_LOG_KEY_PATTERN = r"raw/(?P<ts>\d{4}/\d{2}/\d{2}/\d{2}/\d{2})/(?P<shortid>\w{22})\.power.log"
	RAW_TIMESTAMP_FORMAT = "%Y/%m/%d/%H/%M"

	FAILED_LOG_KEY_PATTERN = r"failed/(?P<shortid>\w{22})/(?P<ts>\d{4}-\d{2}-\d{2}-\d{2}-\d{2})\.power.log"
	FAILED_TIMESTAMP_FORMAT = "%Y-%m-%d-%H-%M"

	def __init__(self, bucket, key):
		self._bucket = bucket
		self._log_key = key

		if key.startswith("raw"):
			self._state = RawUploadState.NEW

			match = re.match(RawUpload.RAW_LOG_KEY_PATTERN, key)
			if not match:
				raise ValueError("Failed to extract shortid and timestamp from key.")

			fields = match.groupdict()
			self._shortid = fields["shortid"]
			self._timestamp= datetime.strptime(fields["ts"], RawUpload.RAW_TIMESTAMP_FORMAT)

			self._descriptor_key = self._create_raw_descriptor_key(fields["ts"], fields["shortid"])
			self._error_key = None # New RawUploads should never have an error object

		elif key.startswith("failed"):
			self._state = RawUploadState.FAILED

			match = re.match(RawUpload.FAILED_LOG_KEY_PATTERN, key)
			if not match:
				raise ValueError("Failed to extract shortid and timestamp from key.")

			fields = match.groupdict()
			self._shortid = fields["shortid"]
			self._timestamp = datetime.strptime(fields["ts"], RawUpload.FAILED_TIMESTAMP_FORMAT)

			self._descriptor_key = self._create_failed_descriptor_key(fields["ts"], fields["shortid"])
			self._error_key = self._create_failed_error_key(fields["ts"], fields["shortid"])

		else:
			raise NotImplementedError("__init__ is not supported for key pattern: %s" % key)

		self._upload_event_log_bucket = None
		self._upload_event_log_key = None
		self._upload_event_location_populated = False

		# These are loaded lazily from S3
		self._descriptor = None
		self._error = None

	def _create_raw_descriptor_key(self, ts_string, shortid):
		return "raw/%s/%s.descriptor.json" % (ts_string, shortid)

	def _create_failed_descriptor_key(self, ts_string, shortid):
		return "failed/%s/%s.descriptor.json" % (shortid, ts_string)

	def _create_failed_error_key(self, ts_string, shortid):
		return "failed/%s/%s.error.json" % (shortid, ts_string)

	def _create_failed_log_key(self, ts_string, shortid):
		return "failed/%s/%s.power.log" % (shortid, ts_string)

	def make_failed(self, reason):
		if self._upload_event_location_populated:
			aws.S3.delete_object(
				Bucket=self._upload_event_log_bucket,
				Key=self._upload_event_log_key
			)

			self._upload_event_location_populated = False

		ts_string = self.timestamp.strftime(RawUpload.FAILED_TIMESTAMP_FORMAT)

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

		try:
			error_message_json = json.loads(reason)
		except Exception:
			error_message_json = {"reason": reason}

		error_message_json["made_failed_ts"] = datetime.now().isoformat()
		failed_error_key = self._create_failed_error_key(ts_string, self.shortid)
		aws.S3.put_object(
			Key=failed_error_key,
			Body=json.dumps(error_message_json, sort_keys=True, indent=4).encode("utf8"),
			Bucket=self.bucket,
		)

		# Finally remove the two objects from the /raw prefix to avoid that filling up.
		aws.S3.delete_objects(
			Bucket=self.bucket,
			Delete={
				"Objects": [{"Key": self.log_key}, {"Key": self.descriptor_key}]
			}
		)

		self._log_key = failed_log_key
		self._descriptor_key = failed_descriptor_key
		self._error_key = failed_error_key
		self._state = RawUploadState.FAILED

	def prepare_upload_event_log_location(self, upload_event_bucket, upload_event_key):
		self._upload_event_log_bucket = upload_event_bucket
		self._upload_event_log_key = upload_event_key

		copy_source = "%s/%s" % (self.bucket, self.log_key)
		aws.S3.copy_object(
			Bucket=upload_event_bucket,
			Key=upload_event_key,
			CopySource=copy_source,
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
					"Objects": [{"Key": self.log_key}, {"Key": self.descriptor_key}, {"Key": self.error_key}]
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
	def from_sns_message(msg):
		raw_upload = RawUpload(msg["bucket"], msg["log_key"])

		return raw_upload

	@property
	def sns_message(self):
		return {
			"bucket" : self.bucket,
			"log_key" : self.log_key,
			# This is included to make retrieving the tracing ID easier.
			"shortid" : self.shortid,
		}

	@property
	def state(self):
		return self._state

	@property
	def bucket(self):
		return self._bucket

	@property
	def log_key(self):
		return self._log_key

	@property
	def descriptor_key(self):
		return self._descriptor_key

	@property
	def descriptor(self):
		if self._descriptor is None:
			obj = aws.S3.get_object(Bucket=self.bucket, Key=self.descriptor_key)
			self._descriptor = json.load(obj["Body"])

		return self._descriptor

	@property
	def error_key(self):
		return self._error_key

	@property
	def error(self):
		if self._error is None:
			obj = aws.S3.get_object(Bucket=self.bucket, Key=self.error_key)
			self._error = json.load(obj["Body"])

		return self._error

	@property
	def shortid(self):
		return self._shortid

	@property
	def timestamp(self):
		return self._timestamp

	def __str__(self):
		return "%s:%s:%s:%s" % (self.shortid, self.timestamp.isoformat(), self.bucket, self.log_key)



def _generate_upload_path(instance, filename):
	ts = now()
	shortid = instance.shortid
	return _generate_upload_key(ts, shortid)


def _generate_upload_key(ts, shortid):
	timestamp = ts.strftime("%Y/%m/%d/%H/%M")
	return "uploads/%s/%s.power.log" % (timestamp, shortid)


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
	type = IntEnumField(enum=UploadEventType)
	game = models.ForeignKey(
		"games.GameReplay", on_delete=models.SET_NULL,
		null=True, blank=True, related_name="uploads"
	)
	created = models.DateTimeField(auto_now_add=True)
	upload_ip = models.GenericIPAddressField()
	status = IntEnumField(enum=UploadEventStatus, default=UploadEventStatus.UNKNOWN)
	tainted = models.BooleanField(default=False)
	error = models.TextField(blank=True)
	traceback = models.TextField(blank=True)

	metadata = models.TextField()
	file = models.FileField(upload_to=_generate_upload_path)

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
	file = instance.file
	if file.name and default_storage.exists(file.name):
		file.delete(save=False)
