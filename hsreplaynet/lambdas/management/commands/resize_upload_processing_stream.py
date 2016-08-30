from django.core.management.base import BaseCommand
from hsreplaynet.utils.aws.streams import resize_upload_processing_stream


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument(
			"--shards",
			default=4,
			type=int,
			help="The number of shards to make the stream"
		)

	def handle(self, *args, **options):
		num_shards = options["shards"]
		self.stdout.write("Resizing stream to size: %i" % num_shards)
		try:
			resize_upload_processing_stream(num_shards)
		except Exception as e:
			self.stdout.write("ERROR: %s" % str(e))
