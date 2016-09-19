import boto3
from django.conf import settings


if settings.ENV_AWS:
	IAM = boto3.client("iam")
	LAMBDA = boto3.client("lambda")
	KINESIS = boto3.client("kinesis")
	S3 = boto3.client("s3")
else:
	# Stubbed to prevent ImportErrors
	IAM, LAMBDA, KINESIS, S3 = None, None, None, None
