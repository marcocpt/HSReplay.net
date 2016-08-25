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


def get_kinesis_stream_arn_from_name(name):
	stream = KINESIS.describe_stream(
		StreamName=name,
	)
	if stream:
		return stream["StreamDescription"]["StreamARN"]


def publish_raw_upload_to_processing_stream(raw_upload):
	return KINESIS.put_record(
		StreamName=settings.KINESIS_UPLOAD_PROCESSING_STREAM_NAME,
		Data=raw_upload.kinesis_data,
		PartitionKey=raw_upload.kinesis_partition_key,
	)


def get_processing_stream_max_writes_per_second():
	stream = KINESIS.describe_stream(
		StreamName=settings.KINESIS_UPLOAD_PROCESSING_STREAM_NAME,
	)
	num_shards = len(stream["StreamDescription"]["Shards"])
	best_case_throughput = (num_shards * 1000)
	safety_limit = .9
	return best_case_throughput * safety_limit


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
