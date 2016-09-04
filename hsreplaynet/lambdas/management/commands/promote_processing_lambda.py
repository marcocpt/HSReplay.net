import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from hsreplaynet.uploads.models import UploadEvent, UploadEventStatus
from hsreplaynet.utils.aws import LAMBDA


class Command(BaseCommand):
	help = "Promote the ProcessS3CreateObjectV1 lambda into PROD"

	def add_arguments(self, parser):
		parser.add_argument(
			"--bypass_canary", action="store_true", default=False,
			help="Skip the canary stage and promote directly to PROD"
		)

	def handle(self, *args, **options):
		func_name = "ProcessS3CreateObjectV1"

		prod_alias = LAMBDA.get_alias(FunctionName=func_name, Name="PROD")
		self.stdout.write(
			"PROD Alias starting at version: %s" % prod_alias["FunctionVersion"]
		)

		canary_alias = LAMBDA.get_alias(FunctionName=func_name, Name="CANARY")
		self.stdout.write(
			"CANARY Alias starting at version: %s" % canary_alias["FunctionVersion"]
		)

		# Create new version
		self.stdout.write("Publishing new version...")
		new_version = LAMBDA.publish_version(FunctionName=func_name)
		self.stdout.write("New version is: %s" % new_version["Version"])

		# This causes the new code to start getting used on canary upload events.
		update_canary_result = LAMBDA.update_alias(
			FunctionName=func_name,
			Name="CANARY",
			FunctionVersion=new_version["Version"],
		)
		self.stdout.write(
			"CANARY Alias updated to version: %s" % update_canary_result["FunctionVersion"]
		)

		if options["bypass_canary"]:
			# We promote all aliases and return immediately.
			self.stdout.write("Bypassing Canary stage.")
			update_prod_result = LAMBDA.update_alias(
				FunctionName=func_name,
				Name="PROD",
				FunctionVersion=new_version["Version"],
			)
			self.stdout.write(
				"PROD Alias updated to version: %s" % update_prod_result["FunctionVersion"]
			)
			self.stdout.write("Finished.")
			return

		# If we did not exit already, then we are doing a canary deployment.
		canary_period_start = datetime.now()
		min_wait_seconds = settings.MIN_CANARY_WAIT_SECONDS
		max_wait_time = datetime.now() + timedelta(seconds=2 * min_wait_seconds)

		self.stdout.write("Starting Canary Period Wait For %s Seconds" % min_wait_seconds)
		time.sleep(min_wait_seconds)
		min_canary_uploads = settings.MIN_CANARY_UPLOADS
		self.stdout.write("MIN_CANARY_UPLOADS = %s" % min_canary_uploads)

		processing_statuses = UploadEventStatus.processing_statuses()
		wait_for_more_canary_uploads = True
		while wait_for_more_canary_uploads:
			canary_uploads = UploadEvent.objects.filter(
				canary=True,
				created__gte=canary_period_start,
			).exclude(status__in=processing_statuses)

			if canary_uploads.count() >= min_canary_uploads:
				wait_for_more_canary_uploads = False
			else:
				if datetime.now() > max_wait_time:
					msg = "Waited too long for canary events. Exiting"
					self.stderr.write(msg)
					raise RuntimeError(msg)

				self.stdout.write(
					"Found %i uploads... sleeping 3 seconds" % (canary_uploads.count(),)
				)
				time.sleep(3)

		self.stdout.write(
			"%s canary upload events have been found" % canary_uploads.count()
		)
		success = UploadEventStatus.SUCCESS
		canary_failures = [u for u in canary_uploads.all() if u.status != success]

		if canary_failures:
			# We have canary failures, time to rollback.
			self.stdout.write("The following canary uploads have failed:")
			self.stdout.write(", ".join(u.shortid for u in canary_failures))

			update_canary_result = LAMBDA.update_alias(
				FunctionName=func_name,
				Name="CANARY",
				FunctionVersion=prod_alias["FunctionVersion"],
			)
			self.stdout.write(
				"CANARY reverted to version: %s" % update_canary_result["FunctionVersion"]
			)
			raise RuntimeError("Deploy aborted due to canary failures.")

		# We didn't have any canary failures so it's time to promote PROD.
		self.stdout.write("The canary version is a success! Promoting PROD.")
		update_prod_result = LAMBDA.update_alias(
			FunctionName=func_name,
			Name="PROD",
			FunctionVersion=update_canary_result["FunctionVersion"],
		)
		self.stdout.write(
			"PROD Alias updated to version: %s" % update_prod_result["FunctionVersion"]
		)
		self.stdout.write("Finished.")
