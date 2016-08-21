"""
Minimalist Lambda Handlers

This module represents our most mission critical code and has minimal dependencies.

Specific design considerations:
- It is designed to not require DB connectivity
- It does not bootstrap the Django machinery
- It does not depend on hsreplaynet.* modules
- It makes minimal assumptions about the structure of the data it receives

These design considerations mean this lambda can be deployed on a different cycle than
the rest of the hsreplaynet codebase.
"""
import json
import shortuuid
import logging
from base64 import b64decode
from datetime import datetime


logger = logging.getLogger()
logger.setLevel(logging.INFO)

try:
	import boto3
	S3 = boto3.client("s3")
except ImportError:
	S3 = None

S3_RAW_LOG_UPLOAD_BUCKET = "hsreplaynet-uploads"


def get_timestamp():
	return datetime.now()


def get_shortid():
	return shortuuid.uuid()


def get_auth_token(headers):
	if "Authorization" not in headers:
		raise Exception("The Authorization Header is required.")

	auth_components = headers["Authorization"].split()
	if len(auth_components) != 2:
		raise Exception("Authorization header must have a scheme and a token.")

	return auth_components[1]


def generate_log_upload_address_handler(event, context):
	logger.info("***** EVENT INFO *****")
	logger.info(json.dumps(event, sort_keys=True, indent=4))
	gateway_headers = event["headers"]

	auth_token = get_auth_token(gateway_headers)
	shortid = get_shortid()
	ts = get_timestamp()
	ts_path = ts.strftime("%Y/%m/%d/%H/%M")

	logger.info("Token: %s", auth_token)
	logger.info("ShortID: %s", shortid)
	logger.info("Timestamp: %s", ts_path)

	upload_metadata = json.loads(b64decode(event.pop("body")).decode("utf8"))

	descriptor = {
		"gateway_headers": gateway_headers,
		"shortid": shortid,
		"source_ip": event["source_ip"],
		"upload_metadata": upload_metadata,
	}

	s3_descriptor_key = "raw/%s/%s.descriptor.json" % (ts_path, shortid)
	logger.info("S3 Descriptor Key: %s", s3_descriptor_key)

	# S3 only triggers downstream lambdas for PUTs suffixed with '...power.log'
	s3_powerlog_key = "raw/%s/%s.power.log" % (ts_path, shortid)
	logger.info("S3 Powerlog Key: %s", s3_powerlog_key)

	descriptor["event"] = event
	logger.info("***** COMPLETE DESCRIPTOR *****")
	logger.info(json.dumps(descriptor, sort_keys=True, indent=4))

	S3.put_object(
		ACL="private",
		Key=s3_descriptor_key,
		Body=json.dumps(descriptor, sort_keys=True, indent=4).encode("utf8"),
		Bucket=S3_RAW_LOG_UPLOAD_BUCKET
	)

	log_put_expiration = 60 * 60 * 24
	# Only one day, since if it hasn't been used by then it's unlikely to be used.
	presigned_put_url = S3.generate_presigned_url(
		"put_object",
		Params={
			"Bucket": S3_RAW_LOG_UPLOAD_BUCKET,
			"Key": s3_powerlog_key,
			"ContentType": "text/plain",
		},
		ExpiresIn=log_put_expiration,
		HttpMethod="PUT"
	)
	logger.info("Presigned Put URL:\n%s" % presigned_put_url)

	return {
		"put_url": presigned_put_url,
		"upload_shortid": shortid,  # Deprecated (Beta, 2016-08-06)
		"shortid": shortid,
	}
