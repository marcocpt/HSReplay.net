from django.core.management.base import BaseCommand
from hsreplaynet.utils.aws.clients import LAMBDA


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument(
			"lambda",
			help="The name of the lambda stream consumer to disable"
		)
		parser.add_argument(
			"enabled",
			help="Make the consumer enabled, either 'true' or 'false'."
		)

	def handle(self, *args, **options):
		enabled = True if options["enabled"].lower() == "true" else False
		event_source_list = LAMBDA.list_event_source_mappings(
			FunctionName=options["lambda"]
		)
		self.stdout.write("Stream processing for %r will be set to %r" % (
			options["lambda"],
			options["enabled"]
		))

		for mapping in event_source_list["EventSourceMappings"]:
			LAMBDA.update_event_source_mapping(
				UUID=mapping["UUID"],
				Enabled=enabled,
			)
		self.stdout.write("Finished.")
