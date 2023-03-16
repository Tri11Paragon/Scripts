#!/usr/bin/python3

import requests
import json
import argparse
import os

env_locs = {"~/", "~/.local/share/dns_helper/", "./", "../"}

parser = argparse.ArgumentParser(prog="DNS Record Helper",
				 description="Retrieves DNS records",
				 epilog="Now a general superscript!")

parser.add_argument('-l', '--list', action='store_true', help="List all DNS records")
parser.add_argument('-a', '--arecords', action='store_true', help="Only list A records")
parser.add_argument('-c', '--cname', action='store_true', help="Only list CNAME records")
parser.add_argument('-n', '--name', default=None, nargs='?', const='envf', help="Only records with this name")
parser.add_argument('-i', '--ip', action='store_true', help="Only print the IP of name")
parser.add_argument('-z', '--zone', default=None, help="Cloudflare Zone ID")
parser.add_argument('-k', '--auth', default=None, help="Cloudflare Auth Key")

args = parser.parse_args()

def get_zones(authkey):
	zone_req = requests.get("https://api.cloudflare.com/client/v4/zones",
					headers = {
						"Content-Type": "application/json",
						"Authorization": "Bearer " + authkey})
	if zone_req.status_code != 200:
		print("Error requesting zones! Status Code:")
		print(zone_req.status_code)
		print("Text")
		print(zone_req.text)
	return zone_req

class zone_processor:
	def __init__(self, zoneid, authkey, filter):
		self.requ = requests.get("https://api.cloudflare.com/client/v4/zones/" + zoneid + "/dns_records",
					headers = {
						"Content-Type": "application/json",
						"Authorization": "Bearer " + authkey})
		self.filter = filter

	def print_content(self, row):
		if args.ip:
			print(row['content'])
		else:
			print(row['name'] + ":\t" + row['content'])

	def process_raw_row(self, row):
		if args.list:
			print(row['name'] + " (" + row['type'] + "):\t" + row['content'])
		elif args.arecords:
			if row['type'] == "A":
				self.print_content(row)
		elif args.cname:
			if row['type'] == "CNAME":
				self.print_content(row)
		else:
			print(row)

	def process_named_row(self, row, name):
		if row['name'] == name:
			if args.arecords:
				if row['type'] == "A":
					self.print_content(row)
			else:
				self.print_content(row)

	def process_row(self, row):
		if self.filter is None:
			self.process_raw_row(row)
		else:
			self.process_named_row(row, self.filter)

	def process(self):
		if self.requ.status_code == 200:
			parse = json.loads(self.requ.text)
			for r in parse['result']:
				self.process_row(r)
		else:
			print("Error sending request, status code: ")
			print(self.requ.status_code)
			print("Text:")
			print(self.requ.text)

if __name__ == "__main__":
	env_results = None
	for f in env_locs:
		path = f + "dns_resolv_env.json"
		if os.path.exists(path):
			envf = open(path, 'r')
			env_results = json.load(envf)
			break

	auth = args.auth
	zone = args.zone
	name = args.name

	if env_results is not None:
		if 'default_name' in env_results and name == "envf":
			name = env_results['default_name']
		if 'zone_id' in env_results and zone is None:
			zone = env_results['zone_id']
		if 'auth_key' in env_results and auth is None:
			auth = env_results['auth_key']

	if auth is None:
		print("You must specify an auth key (either via dns_resolv_env.json file or with --auth)")
		exit(-1)

	if zone is None:
		zones = get_zones(auth)
		parsed_zones = json.loads(zones.text)
		for r in parsed_zones['result']:
			zp = zone_processor(r['id'], auth, name)
			zp.process();
	else:
		z = zone_processor(zone, auth, name)
		z.process()

