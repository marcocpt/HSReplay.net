from django.conf import settings
from django.core.management.base import BaseCommand
from hsreplaynet.games.models import GameReplay, _generate_upload_path as replay_path
from hsreplaynet.utils.aws import S3
from ...models import UploadEvent, _generate_upload_path as upload_event_path


class Command(BaseCommand):
	help = "Update the media paths for Uploads and GameReplays"

	def handle(self, *args, **options):
		self.bucket = settings.AWS_STORAGE_BUCKET_NAME
		self.stdout.write("Using bucket %r" % (self.bucket))

		self.delete = []

		uploads = list(UploadEvent.objects.all())
		self.stdout.write("Found %i UploadEvents" % (len(uploads)))
		for upload in uploads:
			old_path = upload.file.name
			new_path = upload_event_path(upload, old_path)
			self._update_path(upload, old_path, new_path, field="file")

		replays = list(GameReplay.objects.all())
		self.stdout.write("Found %i GameReplays" % (len(replays)))
		for replay in replays:
			old_path = replay.replay_xml.name
			new_path = replay_path(replay, old_path)
			self._update_path(replay, old_path, new_path, field="replay_xml")

		self.cleanup()

	def _update_path(self, obj, old_path, new_path, field):
		if new_path != old_path:
			self.stdout.write("Updating %r -> %r" % (old_path, new_path))
			self._s3_copy(old_path, new_path)
			setattr(obj, field, new_path)
			obj.save()
			self.delete.append(old_path)

	def _s3_copy(self, old_path, new_path):
		source = "%s/%s" % (self.bucket, old_path)
		S3.copy_object(Bucket=self.bucket, Key=new_path, CopySource=source)

	def cleanup(self):
		print("Deleting the following files:\n%s" % "\n".join(self.delete))

		S3.delete_objects(
			Bucket=self.bucket,
			Delete={
				"Objects": [{"Key": k} for k in self.delete],
			}
		)
