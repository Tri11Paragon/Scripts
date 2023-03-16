# Scripts

General useful scripts (mostly for Linux)

# dns_fetch.py
This lovely python script allows you to fetch ip address form cloudflare dns records. Useful for remote servers with dynamic ips. You can define the env file "dns_resolv_env.json" as follows:
```
{
        "auth_key": "key here (required without --auth)",
        "zone_id": "zone id here (optional)",
        "default_name": "website name here (optional)"
}
```
The script has many useful featues:
- `python3 dns_fetch.py -a -n -i` which will return only the ip address of the A record corresponding to default_name.
    - This can be used in bash commands: `ssh username@$(python3 dns_fetch.py -a -n -i)`
- `python3 dns_fetch.py -a` will return all A records
- `python3 dns_fetch.py -c` will return all CNAME records
- `python3 dns_fetch.py` will print the raw json from cloudflare
- `python3 dns_fetch.py -n` will print all records corresponding to default_name