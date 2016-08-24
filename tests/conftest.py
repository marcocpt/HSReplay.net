import pytest
from django.core.management import call_command
from base64 import b64encode


def pytest_addoption(parser):
	parser.addoption(
		"--all",
		action="store_true",
		help="run slower tests not enabled by default"
	)


@pytest.mark.django_db
@pytest.yield_fixture(scope="session")
def hsreplaynet_card_db():
	call_command("load_cards")
	yield None


@pytest.yield_fixture(scope="session")
def upload_context():
	yield None


@pytest.yield_fixture(scope="session")
def upload_event():
	yield {
		"headers": {
			"Authorization": "Token beh7141d-c437-4bfe-995e-1b3a975094b1",
		},
		"body": b64encode('{"player1_rank": 5}'.encode("utf8")).decode("ascii"),
		"source_ip": "127.0.0.1",
	}


@pytest.yield_fixture(scope="session")
def s3_create_object_event():
	yield {
		"Records": [{
			"s3": {
				"bucket": {
					"name": "hsreplaynet-raw-log-uploads",
				},
				"object": {
					"key": "raw/2016/07/20/10/37/hUHupxzE9GfBGoEE8ECQiN/power.log",
				}
			}
		}]
	}
