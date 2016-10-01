"""Lambdas written to be executed as a cron operation.

The cron schedule for these must be setup via the AWS Web Console.
"""
import re
from collections import defaultdict
from datetime import datetime, date, timedelta
from django.conf import settings
from hsreplaynet.uploads.models import RawUpload, UploadEvent
from hsreplaynet.utils import instrumentation, log, aws
from hsreplaynet.utils.influx import influx_metric


@instrumentation.lambda_handler(cpu_seconds=180)
def reap_orphan_descriptors_handler(event, context):
	"""A daily job to cleanup orphan descriptors in the raw uploads bucket."""
	current_date = date.now()
	reaping_delay = settings.LAMBDA_ORPHAN_REAPING_DELAY_DAYS
	assert reaping_delay >= 1  # Protect against descriptors just created
	reaping_date = current_date - timedelta(days=reaping_delay)
	log.info("Reaping Orphan Descriptors For: %r", reaping_date.isoformat())

	inventory = get_reaping_inventory_for_date(reaping_date)

	for hour, hour_inventory in inventory.items():
		reaped_orphan_count = 0
		for minute, minute_inventory in hour_inventory.items():
			for shortid, keys in minute_inventory.items():
				if is_safe_to_reap(shortid, keys):
					log.info("Reaping Descriptor: %r", keys["descriptor"])
					aws.S3.delete_object(
						Bucket=settings.S3_RAW_LOG_UPLOAD_BUCKET,
						Key=keys["descriptor"]
					)
					reaped_orphan_count += 1
				else:
					log.info("Skipping Descriptor: %r (Unsafe To Reap)", keys["descriptor"])

		log.info(
			"A total of %s descriptors reaped for hour: %s" % (
				str(reaped_orphan_count),
				str(hour)
			)
		)

		# Report count of orphans to Influx
		fields = {
			"count": reaped_orphan_count
		}

		influx_metric(
			"orphan_descriptors_reaped",
			fields=fields,
			timestamp=reaping_date,
			hour=hour
		)
	log.info("Finished.")


def is_safe_to_reap(shortid, keys):
	if "log" in keys:
		# If a log for the shortid exists it's not an orphan descriptor
		# It's more likely data we're having trouble processing
		return False

	if UploadEvent.objects.filter(shortid=shortid).exists():
		# If an upload event for the shortid exists it's not an orphan
		return False


def get_reaping_inventory_for_date(date):
	descriptors = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
	key_prefix = date.strftime("raw/%Y/%m/%d")

	for object in aws.list_all_objects_in(
		settings.S3_RAW_LOG_UPLOAD_BUCKET,
		prefix=key_prefix
	):
		key = object["Key"]

		if key.endswith("descriptor.json"):
			match = re.match(RawUpload.DESCRIPTOR_KEY_PATTERN, key)
			fields = match.groupdict()
			shortid = fields["shortid"]
			timestamp = datetime.strptime(fields["ts"], RawUpload.TIMESTAMP_FORMAT)
			descriptors[timestamp.hour][timestamp.minute][shortid]["descriptor"] = key
		else:
			match = re.match(RawUpload.RAW_LOG_KEY_PATTERN, key)
			fields = match.groupdict()
			shortid = fields["shortid"]
			timestamp = datetime.strptime(fields["ts"], RawUpload.TIMESTAMP_FORMAT)

			descriptors[timestamp.hour][timestamp.minute][shortid]["log"] = key

	return descriptors
