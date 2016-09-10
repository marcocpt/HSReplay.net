import boto3
from django.conf import settings


if settings.ENV_DEV:
	# On DEV, we do not have a region and we do not want
	# to connect to AWS. We stub to avoid ImportErrors.
	IAM, LAMBDA, KINESIS, S3 = None, None, None, None
else:
	IAM = boto3.client("iam")
	LAMBDA = boto3.client("lambda")
	KINESIS = boto3.client("kinesis")
	S3 = boto3.client("s3")
