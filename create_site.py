#!/bin/python3

import argparse
import subprocess
import color_io

parser = argparse.ArgumentParser(prog='Site Generator', description='Apache/Nginx Site Generator', epilog='Currently Only For Nginx')

parse_type_group = parser.add_mutually_exclusive_group()

parse_type_group.add_argument('-p', '--proxy', action='store_true', help="Generate a site which will act as a proxy")
parse_type_group.add_argument('-r', '--root', action='store_true', help="Generate a site which serves from a document root")

parser.add_argument('-i', '--install', default="/etc/nginx/sites-available/", help="Set the install location for the generated config, defaults to /etc/nginx/sites-available/")
parser.add_argument('-l', '--log', default="/var/log/nginx/", help="Set the default log location for the generated config, defaults to /var/log/nginx/")
parser.add_argument('-s', '--symb', default="/etc/nginx/sites-enabled/", help="Set the location for the symbolic link to enable the config")

args = parser.parse_args()

install_location = args.install
link_location = args.symb
log_location = args.log

if not install_location.endswith('/'):
	install_location = install_location + "/"
if not log_location.endswith('/'):
	log_location = log_location + "/"

site = {}
site['name'] = color_io.input_print("Enter site address (eg: 'tpgc.me')")

def get_config_name():
	return site['name']

def get_config_path():
	return install_location + get_config_name()

def create_file():
	return open(get_config_path(), 'a')

def create_nginx():
	f = create_file()
	f.write("#--- --- --- {Begin Site " + site['name'] + "} --- --- ---#\n")
	f.write("server {\n")
	f.write("	listen 443 ssl http2;\n\n")
	f.write("	server_name " + site['name'] + ";\n\n")
	f.write("	access_log " + log_location + site['name'] + "-access.log;\n")
	f.write("	error_log " + log_location + site['name'] + "-error.log error;\n\n")
	return f

def end_nginx(f):
	f.write("}\n")
	f.write("#--- --- --- {End Site " + site['name'] + "} --- --- ---#\n\n")
	f.close()
	subprocess.run(["ln", "-s", get_config_path(), link_location + get_config_name()])

def write_location(f, loc, mod):
	f.write("	location " + loc + " {\n")
	for m in mod:
		f.write("		" + m + ";\n")
	f.write("	}\n\n")

def create_proxy():
	color_io.green_print("Creating proxy site")
	site['location'] = color_io.input_print("Enter site location (default '/')", "/")
	site['address'] = color_io.input_print("Enter address to proxy to (default: http://127.0.0.1)", "http://127.0.0.1")
	site['port'] = color_io.input_print("Enter port")
	f = create_nginx()
	write_location(f, site['location'], ["proxy_pass " + site['address'] + ":" + site['port'],
				"proxy_set_header Upgrade $http_upgrade",
				'proxy_set_header Connection "Upgrade"',
				"proxy_set_header Host $host"])
	end_nginx(f)

def create_root():
	color_io.green_print("Creating root site")
	site['path'] = color_io.input_print("Enter site files path")
	f = create_nginx()
	f.write("	root " + site['path'] + ";\n\n");
	f.write("	include php-fpm;\n\n");
	end_nginx(f)

# Process user input based on args provided
def execute_input():
	if args.proxy:
		create_proxy()
	elif args.root:
		create_root()
	else:
		create_proxy()

if __name__ == "__main__":
	execute_input()
