import importlib
from django.core.management.base import BaseCommand
from django.conf import settings
from hsreplaynet.utils.aws import LAMBDA, IAM, get_kinesis_stream_arn_from_name
from hsreplaynet.utils.instrumentation import get_lambda_descriptors


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument("module", help="The comma separated modules to inspect")
		parser.add_argument(
			"artifact", default="hsreplay.zip", help="The path to the lambdas zip artifact"
		)

	def handle(self, *args, **options):
		for module_name in options["module"].split(","):
			importlib.import_module(module_name)

		descriptors = get_lambda_descriptors()
		if not descriptors:
			self.stdout.write("No descriptors found. Exiting.")
			return

		if LAMBDA is None:
			raise Exception("Boto3 is not available")

		all_lambdas = LAMBDA.list_functions()

		response = IAM.get_role(RoleName=settings.LAMBDA_DEFAULT_EXECUTION_ROLE_NAME)
		execution_role_arn = response["Role"]["Arn"]
		self.stdout.write("Execution Role Arn: %r" % (execution_role_arn))

		artifact_path = options["artifact"]
		self.stdout.write("Using code at path: %r" % (artifact_path))

		with open(artifact_path, "rb") as artifact:
			code_payload_bytes = artifact.read()
			self.stdout.write("Code Payload Bytes: %s" % (len(code_payload_bytes)))

			for descriptor in descriptors:
				self.stdout.write("About to deploy: %s" % (descriptor["name"]))

				existing_lambda = None
				for func in all_lambdas["Functions"]:
					if func["FunctionName"] == descriptor["name"]:
						existing_lambda = func

				if existing_lambda:
					self.stdout.write("Lambda exists - will update.")

					LAMBDA.update_function_configuration(
						FunctionName=descriptor["name"],
						Role=execution_role_arn,
						Handler=descriptor["handler"],
						Timeout=descriptor["cpu_seconds"],
						MemorySize=descriptor["memory"],
					)

					LAMBDA.update_function_code(
						FunctionName=descriptor["name"],
						ZipFile=code_payload_bytes,
						Publish=True,
					)

				else:
					self.stdout.write("New Lambda - will create.")

					LAMBDA.create_function(
						FunctionName=descriptor["name"],
						Runtime="python2.7",
						Role=execution_role_arn,
						Handler=descriptor["handler"],
						Code={"ZipFile": code_payload_bytes},
						Timeout=descriptor["cpu_seconds"],
						MemorySize=descriptor["memory"],
						Publish=True,
					)

				if descriptor["stream_name"]:
					# This lambda would like to be registered as a listener on a kinesis stream
					self.stdout.write("Applying event source mapping for stream: %s" % descriptor["stream_name"])
					batch_size = descriptor["stream_batch_size"]
					stream_name = descriptor["stream_name"]
					target_event_source = get_kinesis_stream_arn_from_name(stream_name)

					event_source_list = LAMBDA.list_event_source_mappings(
						FunctionName=descriptor["name"]
					)

					if event_source_list["EventSourceMappings"]:
						# We need to update the existing mappings
						# First we need to remove any stale event source mappings.
						# Then we need to look for an existing match and update it.
						# Finally if we didn't update an existing match, we need to create a new mapping.

						# So long as we don't DELETE an in-use mapping it will not loose its place in the stream.

						update_existing_mapping_success = False

						for mapping in event_source_list["EventSourceMappings"]:

							mapping_uuid = mapping["UUID"]
							mapping_event_source = mapping["EventSourceArn"]
							mapping_batch_size = mapping["BatchSize"]

							if mapping_event_source != target_event_source:
								# Delete this event source, it's stale.
								self.stdout.write("Deleting stale mapping for event source: %s" % mapping_event_source)
								LAMBDA.delete_event_source_mapping(UUID=mapping_uuid)
							else:
								update_existing_mapping_success = True

								if mapping_batch_size != batch_size:
									# The batch size is the only thing that might have changed
									self.stdout.write("Updating existing stream batch size from %s to %s" % (
										mapping_batch_size,
										batch_size
									))
									LAMBDA.update_event_source_mapping(UUID=mapping_uuid, BatchSize=mapping_batch_size)
								else:
									# Nothing has changed.
									self.stdout.write("No changes required.")

						if not update_existing_mapping_success:
							# We didn't find an existing mapping to update, so we still must create one
							self.stdout.write("Creating new mapping for event source: %s" % target_event_source)
							LAMBDA.create_event_source_mapping(
								EventSourceArn=target_event_source,
								FunctionName=descriptor["name"],
								BatchSize=batch_size,
								StartingPosition='TRIM_HORIZON'
							)
					else:
						# No mappings currently exist, so we need to create a new mapping
						self.stdout.write("Creating new mapping for event source: %s" % target_event_source)
						LAMBDA.create_event_source_mapping(
							EventSourceArn=target_event_source,
							FunctionName=descriptor["name"],
							BatchSize=batch_size,
							StartingPosition='TRIM_HORIZON'
						)
