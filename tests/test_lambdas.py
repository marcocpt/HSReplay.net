import json
import shortuuid
from datetime import datetime
from unittest.mock import MagicMock
from hsreplaynet.utils import aws
from isolated import uploaders


def test_upload(upload_event, upload_context, monkeypatch):
	# Control the timestamp and shortid used so we can verify the correct key generation.
	shortid = shortuuid.uuid()
	ts = datetime.now()
	ts_path = ts.strftime("%Y/%m/%d/%H/%M")

	def mock_get_shortid():
		return shortid
	monkeypatch.setattr(uploaders, "get_shortid", mock_get_shortid)

	def mock_get_timestamp():
			return ts
	monkeypatch.setattr(uploaders, "get_timestamp", mock_get_timestamp)

	expected_descriptor_key = "raw/%s/%s.descriptor.json" % (ts_path, shortid)

	# Mock out S3
	mock_s3 = MagicMock()
	mock_s3.put_object = MagicMock()
	mock_s3.generate_presigned_url = MagicMock(return_value="[A SIGNED URL]")
	monkeypatch.setattr(uploaders, "S3", mock_s3)

	# Invoke code under test
	result = uploaders.generate_log_upload_address_handler(upload_event, upload_context)

	# Start verification
	actual_put_args = mock_s3.put_object.call_args[1]
	descriptor_key = actual_put_args["Key"]
	assert descriptor_key == expected_descriptor_key

	descriptor_object_bytes = actual_put_args["Body"]
	descriptor = json.loads(descriptor_object_bytes.decode("utf8"))

	assert "descriptor_url" in result
	assert result["descriptor_url"] == "[A SIGNED URL]"
	assert "put_url" in result
	assert result["put_url"] == "[A SIGNED URL]"

	assert "upload_shortid" in result
	# Ensure the shortID returned is also saved to use on the upload event
	assert descriptor["shortid"] == result["upload_shortid"]


def test_process_s3_object(s3_create_object_event, upload_context, monkeypatch):
	# Mock out S3
	mock_s3 = MagicMock()
	mock_s3.put_object = MagicMock()
	mock_s3.get_object = MagicMock()

	mock_s3.generate_presigned_url = MagicMock(return_value="[A SIGNED URL]")
	monkeypatch.setattr(aws, "S3", mock_s3)

	# Invoke code under test
	# result = process_s3_object(s3_create_object_event, upload_context)
