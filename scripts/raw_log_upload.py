"""
This command line tool is intended to simulate HDT uploading a raw log to the web server.
"""
import argparse
import os
import requests
from datetime import datetime


parser = argparse.ArgumentParser(description="Upload a raw log file.")
parser.add_argument(
	"-m", "--metadata_path", help="path to the .json file with metadata to send"
)
parser.add_argument("-a", "--api_key", help="An hsreplay.net API Key")
parser.add_argument("-t", "--auth_token", help="An hsreplay.net AuthToken")
parser.add_argument("log_path", help="path to the power.log file to upload")

args = parser.parse_args()

HOST = "https://upload.hsreplay.net/api/v1/replay/upload/request"
api_key = args.api_key or os.environ.get("HSREPLAYNET_API_KEY")
auth_token = args.auth_token or os.environ.get("HSREPLAYNET_AUTH_TOKEN")

request_one_headers = {
	"X-Api-Key": api_key,
	"Authorization": "Token %s" % (auth_token),
}

if args.metadata_path:
	metadata = open(args.metadata_path).read()
else:
	metadata = {
		"build": 13740,
		"match_start": datetime.now().isoformat()
	}

response_one = requests.post(HOST, json=metadata, headers=request_one_headers).json()
descriptor = requests.get(response_one["descriptor_url"]).content.decode("utf8")

log = open(args.log_path).read()

request_two_headers = {
	"Content-Type": "text/plain"
}

response_two = requests.put(response_one["put_url"], data=log, headers=request_two_headers)

print("PUT Response Code: %s" % response_two.status_code)
print("Replay ID: %s" % response_one["upload_shortid"])
print("Put URL:\n%s" % response_one["put_url"])
print("Descriptor URL:\n%s" % response_one["descriptor_url"])
print(descriptor)
