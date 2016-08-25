import time
import logging
from math import ceil, log, pow
from django.conf import settings
from hsreplaynet.utils.influx import get_avg_upload_processing_seconds
from hsreplaynet.uploads.processing import current_raw_upload_bucket_size

try:
	import boto3
	S3 = boto3.client("s3")
	SNS = boto3.client("sns")
	LAMBDA = boto3.client("lambda")
	IAM = boto3.client("iam")
	KINESIS = boto3.client('kinesis')
	CLOUDWATCH = boto3.client('cloudwatch')
except ImportError:
	S3 = None
	SNS = None
	LAMBDA = None
	IAM = None
	KINESIS = None
	CLOUDWATCH = None

logger = logging.getLogger("hsreplaynet")


def fill_stream_from_iterable(iter, func):
	"""
	Invoke func on the next item from iter at the maximum throughput
	the stream currently supports.
	"""
	pass


def resize_upload_processing_stream():
	"""Entry point for periodic job to tune the upload processing stream size."""
	sla_seconds = settings.KINESIS_STREAM_PROCESSING_THROUGHPUT_SLA_SECONDS
	num_records = current_raw_upload_bucket_size()
	processing_duration = get_avg_upload_processing_seconds()

	resize_stream(
		settings.KINESIS_UPLOAD_PROCESSING_STREAM_NAME,
		num_records,
		processing_duration,
		sla_seconds,
		settings.KINESIS_UPLOAD_PROCESSING_STREAM_MIN_SHARDS,
		settings.KINESIS_UPLOAD_PROCESSING_STREAM_MAX_SHARDS
	)


def resize_stream(
	stream_name, backlog_size, processing_duration,
	sla_seconds=600, min_shards=2, max_shards=32
):
	"""Generic logic for dynamically resizing a kinesis stream"""

	logger.info("Resize initiated for stream: %s", stream_name)
	logger.info(
		"Backlog Size: %s, Processing Duration: %s, SLA Seconds: %s",
		backlog_size,
		processing_duration,
		sla_seconds
	)

	minimum_target_shards = shards_required_for_sla(
		backlog_size,
		processing_duration,
		sla_seconds
	)
	logger.info("Minimum required shards to hit SLA is: %s", minimum_target_shards)

	# increase target shards to the next power of 2
	# so that our split and merge operations are easy
	shard_target = base_two_shard_target(minimum_target_shards)
	logger.info("Base two shards required to hit SLA is: %s", shard_target)

	new_shards_number = min(max_shards, max(min_shards, shard_target))
	logger.info("Final new shard number will be: %s", new_shards_number)

	resize_stream_to_size(stream_name, new_shards_number)


def shards_required_for_sla(num_records, processing_duration, sla_seconds):
	"""Calculate how many shards are required to hit the target SLA"""
	return ceil((1.0 * num_records * processing_duration) / sla_seconds)


def base_two_shard_target(target):
	return pow(2, ceil(log(target, 2)))


def get_open_shards(stream_name):
	wait_for_stream_ready(stream_name)
	sinfo = KINESIS.describe_stream(StreamName=stream_name)
	shards = sinfo["StreamDescription"]["Shards"]
	open_shards = list(filter(shard_is_open, shards))
	return open_shards


def current_stream_size(stream_name):
	return len(get_open_shards(stream_name))


def current_stream_status(stream_name):
	sinfo = KINESIS.describe_stream(StreamName=stream_name)
	return sinfo["StreamDescription"]["StreamStatus"]


def is_base_two_compatible(num):
	return log(num, 2).is_integer()


def resize_stream_to_size(stream_name, target_num_shards):
	# We only resize along powers of 2 to make programmatic merging and splitting
	# of the PartitionKey space easy to keep balanced.
	assert is_base_two_compatible(target_num_shards)

	current_size = current_stream_size(stream_name)
	logger.info("The current size is: %s", current_size)

	resizing_iterations = 1
	while target_num_shards != current_size:
		logger.info("Starting resizing iteration %s", resizing_iterations)

		if target_num_shards > current_size:
			logger.info("The shards will be split.")
			split_shards(stream_name)
		else:
			logger.info("The shards will be merged.")
			merge_shards(stream_name)

		resizing_iterations += 1
		current_size = current_stream_size(stream_name)
		logger.info("The current size is: %s", current_size)

	logger.info("The stream is the correct target size. Finished.")


def wait_for_stream_ready(stream_name):
	# We will wait for up to 1 minute for the stream to become active
	stream_status = current_stream_status(stream_name)
	logger.info("The current stream status is: %s", stream_status)

	attempts = 0
	max_attempts = 15
	while stream_status != "ACTIVE" and attempts < max_attempts:
		time.sleep(4)
		stream_status = current_stream_status(stream_name)
		logger.info("The current stream status is: %s", stream_status)

	if stream_status != "ACTIVE":
		raise Exception("The stream %s never became active!" % stream_name)


def split_shards(stream_name):
	shards = get_open_shards(stream_name)

	logger.info("There are %s shards to split", len(shards))
	while len(shards):
		next_shard_to_split = shards.pop(0)
		logger.info("The next shard to split is: %s", next_shard_to_split["ShardId"])
		wait_for_stream_ready(stream_name)

		starting_hash_key = int(next_shard_to_split["HashKeyRange"]["StartingHashKey"])
		logger.info("Shard starting hash key: %s", str(starting_hash_key))

		ending_hash_key = int(next_shard_to_split["HashKeyRange"]["EndingHashKey"])
		logger.info("Shard ending hash key: %s", str(ending_hash_key))

		combined_hash_key = starting_hash_key + ending_hash_key
		logger.info("The combined hash key: %s", combined_hash_key)

		split_point_hash_key = '{:.0f}'.format((combined_hash_key / 2))
		logger.info("Shard split point hash key: %s", split_point_hash_key)

		KINESIS.split_shard(
			StreamName=stream_name,
			ShardToSplit=next_shard_to_split["ShardId"],
			NewStartingHashKey=str(split_point_hash_key)
		)
	logger.info("Splitting is complete")


def merge_shards(stream_name):
	shards = get_open_shards(stream_name)
	mergable_shard_tuples = prepare_shards_for_merging(shards)

	logger.info("There are %s merges to perform", len(mergable_shard_tuples))
	while len(mergable_shard_tuples):
		first_shard, second_shard = mergable_shard_tuples.pop(0)
		logger.info(
			"The next two shards to be merged are: (%s, %s)",
			first_shard["ShardId"],
			second_shard["ShardId"]
		)
		wait_for_stream_ready(stream_name)

		KINESIS.merge_shards(
			StreamName=stream_name,
			ShardToMerge=first_shard["ShardId"],
			AdjacentShardToMerge=second_shard["ShardId"]
		)
	logger.info("The merging is complete")


def shard_is_open(s):
	return "EndingSequenceNumber" not in s["SequenceNumberRange"]


def shards_are_mergable(first, second):
	first_end_range = int(first["HashKeyRange"]["EndingHashKey"])
	second_start_range = int(second["HashKeyRange"]["StartingHashKey"])
	return (first_end_range + 1) == second_start_range


def prepare_shards_for_merging(shards):

	logger.info("The shards are being prepared for merging")
	sorted_shards = sorted(shards, key=lambda s: int(s["HashKeyRange"]["EndingHashKey"]))

	less_than_two_shards = len(sorted_shards) < 2
	uneven_number_of_shards = len(sorted_shards) % 2 != 0
	if less_than_two_shards or uneven_number_of_shards:
		# Don't attempt to return a result if we have less than 2 shards
		# Or if we don't have an event number of shards

		if less_than_two_shards:
			logger.info("There are less than 2 shards. No merging will be done.")

		if uneven_number_of_shards:
			logger.info("There are an uneven number of shards. No merging will be done.")

		return []

	result = []
	it = iter(sorted_shards)
	for x in it:
		first_shard = x
		second_shard = next(it)
		assert shards_are_mergable(first_shard, second_shard)
		result.append((first_shard, second_shard))

	return result
