import json
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from hsreplaynet.accounts.models import User
from hsreplaynet.uploads.models import UploadEvent


class Command(BaseCommand):
	def add_arguments(self, parser):
		parser.add_argument("file", nargs="+")
		parser.add_argument(
			"--username", nargs="?", type=str,
			help="User to attach the resulting replays to"
		)

	def handle(self, *args, **options):
		username = options["username"]
		if username:
			user = User.objects.get(username=username)
		else:
			user = None

		for file in options["file"]:
			print("Uploading %r" % (file))
			metadata = {
				"build": 0,
				"match_start": now().isoformat(),
			}

			event = UploadEvent(
				upload_ip="127.0.0.1",
				metadata=json.dumps(metadata),
			)

			event.file = file
			event.save()

			with open(file, "r") as f:
				event.file = File(f)
				event.save()

			event.process()
			self.stdout.write("%r: %s" % (event, event.get_absolute_url()))

			if event.game:
				event.game.user = user
				event.game.save()
				self.stdout.write("%r: %s" % (event.game, event.game.get_absolute_url()))
				self.stdout.write("Replay: %s" % (event.game.replay_xml.url))
