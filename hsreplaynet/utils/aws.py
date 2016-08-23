import json
from django.conf import settings

try:
	import boto3
	S3 = boto3.client("s3")
	SNS = boto3.client("sns")
	LAMBDA = boto3.client("lambda")
	IAM = boto3.client("iam")
	KINESIS = boto3.client('kinesis')
except ImportError:
	S3 = None
	SNS = None
	LAMBDA = None
	IAM = None
	KINESIS = None


def get_sns_topic_arn_from_name(name):
	response = SNS.list_topics()

	for topic in response["Topics"]:
		if topic["TopicArn"].split(":")[-1] == name:
			return topic["TopicArn"]


def get_kinesis_stream_arn_from_name(name):
	stream = KINESIS.describe_stream(
		StreamName=name,
	)
	if stream:
		return stream["StreamDescription"]["StreamARN"]


def enable_processing_raw_uploads():
	processing_lambda = LAMBDA.get_function(FunctionName="ProcessS3CreateObjectV1")
	S3.put_bucket_notification_configuration(
		Bucket=settings.S3_RAW_LOG_UPLOAD_BUCKET,
		NotificationConfiguration={
			"LambdaFunctionConfigurations": [{
				"LambdaFunctionArn": processing_lambda["Configuration"]["FunctionArn"],
				"Events": ["s3:ObjectCreated:*"],
				"Id": "TriggerLambdaOnLogCreate",
				"Filter": {
					"Key": {
						"FilterRules": [
							{"Name": "suffix", "Value": "power.log"},
							{"Name": "prefix", "Value": "raw"},
						]
					}
				}
			}]
		}
	)


def disable_processing_raw_uploads():
	# Remove any existing event notification rules by
	# putting an empty configuration on the bucket
	S3.put_bucket_notification_configuration(
		Bucket=settings.S3_RAW_LOG_UPLOAD_BUCKET,
		NotificationConfiguration={}
	)


def publish_sns_message(topic, message):
	return SNS.publish(
		TopicArn=topic,
		Message=json.dumps({"default": json.dumps(message)}),
		MessageStructure="json"
	)


def list_all_objects_in(bucket, prefix=None):
	list_response = S3.list_objects_v2(Bucket=bucket, Prefix=prefix)
	if list_response["KeyCount"] > 0:
		objects = list_response["Contents"]
		while objects:
			yield objects.pop(0)
			if list_response["IsTruncated"] and not objects:
				list_response = S3.list_objects_v2(
					Bucket=bucket,
					Prefix=prefix,
					ContinuationToken=list_response["NextContinuationToken"]
				)
				objects += list_response["Contents"]
