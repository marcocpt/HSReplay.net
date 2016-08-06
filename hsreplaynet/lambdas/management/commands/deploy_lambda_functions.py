import importlib
from django.core.management.base import BaseCommand
from django.conf import settings
from hsreplaynet.utils.aws import LAMBDA, IAM
from hsreplaynet.utils.instrumentation import get_lambda_descriptors


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument("module", help="The comma separated modules to inspect")
		parser.add_argument("artifact", default="hsreplay.zip", help="The path to the lambdas zip artifact")

	def handle(self, *args, **options):
		for module_name in options["module"].split(","):
			module = importlib.import_module(module_name)

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
						FunctionName = descriptor["name"],
						Role = execution_role_arn,
						Handler = descriptor["handler"],
						Timeout = descriptor["cpu_seconds"],
						MemorySize = descriptor["memory"],
					)

					LAMBDA.update_function_code(
						FunctionName = descriptor["name"],
						ZipFile = code_payload_bytes,
						Publish = True
					)

				else:
					self.stdout.write("New Lambda - will create.")

					result = LAMBDA.create_function(
						FunctionName = descriptor["name"],
						Runtime = "python2.7",
						Role = execution_role_arn,
						Handler = descriptor["handler"],
						Code = {"ZipFile":code_payload_bytes},
						Timeout = descriptor["cpu_seconds"],
						MemorySize = descriptor["memory"],
						Publish = True
					)
