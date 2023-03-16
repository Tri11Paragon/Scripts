# Scripts

General useful scripts (mostly for Linux)

# dns_fetch.py
---
This lovely python script allows you to fetch ip address form cloudflare dns records. Useful for remote servers with dynamic ips. You can define the env file "dns_resolv_env.json" as follows:
```
{
        "auth_key": "key here",
        "zone_id": "zone id here",
        "default_name": "website name here"
}
```
### Notes
---
- The env file itself is optional but the script will require you to pass your auth key with `--auth "key here"`
- If no zone id is provided the script will fetch and print from ALL zones on your cloudflare account.
- If default_name is not specified by either file or via `-n "name"`, filtering will be ignored
### Usage Examples
---
- `python3 dns_fetch.py -a -n -i` 
    - Returns only the ip address of the A record corresponding to default_name.
        - This can be used in bash commands: `ssh username@$(python3 dns_fetch.py -a -n -i)`
- `python3 dns_fetch.py -a` 
    - Returns all A records
- `python3 dns_fetch.py -c`
    - Returns all CNAME records
- `python3 dns_fetch.py`
    - Prints the raw json from cloudflare
- `python3 dns_fetch.py -n`
    - Prints all records corresponding to default_name