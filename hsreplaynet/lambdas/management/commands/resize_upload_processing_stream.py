from django.core.management.base import BaseCommand
from hsreplaynet.utils.aws.streams import resize_upload_processing_stream


class Command(BaseCommand):

	def handle(self, *args, **options):
		resize_upload_processing_stream()
