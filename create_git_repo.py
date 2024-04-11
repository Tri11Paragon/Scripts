#!/usr/bin/python3

import requests
import json
import argparse
import os

parser = argparse.ArgumentParser(
                    prog='Repo Creator',
                    description='Create Git Repos on Gitea and Github',
                    epilog='Hello')

parser.add_argument('repo_name')
parser.add_argument('-e', help="environment file", required=False, default=None)
parser.add_argument('-d', '--description', default = "")

args = parser.parse_args()

github_token = ''
gitea_token = ''

if args.e is not None:
	f = open(args.e, "rt")
	values = {}
	for line in f:
		if line.startswith("export"):
			content = line.split("=")
			for idx, c in enumerate(content):
				content[idx] = c.replace("export", "").strip()
			values[content[0]] = content[1].replace("\"", "").replace("'", "")
	try:
		github_token = values["github_token"]
	except Exception:
		print("Failed to parse github token")
	try:
		gitea_token = values["gitea_token"]
	except:
		print("Failed to parse gitea token!")
else:
	github_token = os.environ["github_token"]
	gitea_token = os.environ["gitea_token"]

# GitHub credentials
github_username = 'tri11paragon'

# Gitea credentials
gitea_username = 'tri11paragon'
gitea_url = 'https://git.tpgc.me'

# Repository name
repo_name = args.repo_name

# GitHub API endpoint for creating a repository
github_url = f'https://api.github.com/user/repos'
github_payload = {
    'name': repo_name,
	'description': args.description,
    'private': False  # Set to True if you want a private repository
}
github_headers = {
    'Authorization': f'token {github_token}',
    'Accept': 'application/vnd.github.v3+json'
}

# Create repository on GitHub
response = requests.post(github_url, json=github_payload, headers=github_headers)
if response.status_code == 201:
    print(f"GitHub repository '{repo_name}' created successfully.")
else:
    print(f"Failed to create GitHub repository. Status code: {response.status_code}")
    print(response.text)
    #exit()

# Gitea API endpoint for creating a repository
#gitea_url = f'{gitea_url}/api/v1/user/repos'
gitea_url = f'{gitea_url}/api/v1/repos/migrate'
gitea_payload = {
	'auth_token': github_token,
	'auth_username': github_username,
	'clone_addr': f'https://github.com/{github_username}/{repo_name}.git',
	'description': args.description,
	"issues": True,
	"labels": True,
	"lfs": False,
	"mirror": True,
	"mirror_interval": "1h",
	"pull_requests": True,
	"releases": True,
	"service": "github",
	"wiki": True,
    'repo_name': repo_name,
    'repo_owner': gitea_username,
    'private': False  # Set to True if you want a private repository
}
gitea_headers = {
    'Authorization': f'token {gitea_token}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

# Create repository on Gitea
response = requests.post(gitea_url, json=gitea_payload, headers=gitea_headers)
if response.status_code == 201:
    print(f"Gitea repository '{repo_name}' created successfully.")
else:
    print(f"Failed to create Gitea repository. Status code: {response.status_code}")
    print(response.text)
    #exit()

# gitea_url_add_mirror = f'{gitea_url}/api/v1/repos/{gitea_username}/{repo_name}/mirror'

# print(gitea_url_add_mirror)

# # Payload for adding a mirror
# gitea_payload_add_mirror = {
#     'name': 'GitHub Mirror',
#     'url': f'https://github.com/{github_username}/{repo_name}.git',
#     'repo_user': github_username,
#     'repo_passwd': github_token,
#     'interval': '1h',  # Adjust this as needed, e.g., '1h' for every hour
#     'external': True,
# }

# # Add mirror on Gitea
# response = requests.post(gitea_url_add_mirror, json=gitea_payload_add_mirror, headers=gitea_headers)

# # Check if the mirror was set up successfully
# if response.status_code == 200:
#     print(f"Gitea repository '{repo_name}' set to mirror GitHub repository successfully.")
# else:
#     print(f"Failed to set up mirror on Gitea repository. Status code: {response.status_code}")
#     print(response.text)

# # Set the repository name
# repo_name = args.repo_name

# # GitHub API endpoint for creating a repository
# github_url = f'https://api.github.com/user/repos'

# # JSON payload for the GitHub repository creation request
# github_payload = {
#     'name': repo_name,
#     'private': False,  # Set to True if you want a private repository
#     # You can add more options like description, homepage, etc. if needed
# }

# # Headers containing the GitHub authorization token
# github_headers = {
#     'Authorization': f'token {github_token}',
#     'Accept': 'application/vnd.github.v3+json'
# }

# # Make POST request to create the GitHub repository
# response = requests.post(github_url, json=github_payload, headers=github_headers)

# # Check if the GitHub repository was created successfully
# if response.status_code == 201:
#     print(f"GitHub repository '{repo_name}' created successfully.")
# else:
#     print(f"Failed to create GitHub repository. Status code: {response.status_code}")
#     print(response.text)
#     exit()

# # Gitea API endpoint for creating a repository
# gitea_url = f'{gitea_url}/api/v1/user/repos'

# # JSON payload for the Gitea repository creation request
# gitea_payload = {
#     'name': repo_name,
#     'private': False,  # Set to True if you want a private repository
#     # You can add more options like description, homepage, etc. if needed
# }

# # Headers containing the Gitea authorization token
# gitea_headers = {
#     'Authorization': f'token {gitea_token}',
#     'Accept': 'application/json',
#     'Content-Type': 'application/json'
# }

# # Make POST request to create the Gitea repository
# response = requests.post(gitea_url, json=gitea_payload, headers=gitea_headers)

# # Check if the Gitea repository was created successfully
# if response.status_code == 201:
#     print(f"Gitea repository '{repo_name}' created successfully.")
# else:
#     print(f"Failed to create Gitea repository. Status code: {response.status_code}")
#     print(response.text)
#     exit()

# # Set up Gitea repository to push commits to GitHub repository
# gitea_repo_full_name = f'{gitea_username}/{repo_name}'
# gitea_repo_url = f'{gitea_url}/{gitea_repo_full_name}/git/mirror'
# gitea_mirror_payload = {
#     'repo_name': f'{github_username}/{repo_name}',
#     'repo_user': github_username,
#     'repo_pass': github_token,
#     'mirror_interval': '1h',  # You can adjust this interval as needed
# }
# response = requests.post(gitea_repo_url, json=gitea_mirror_payload, headers=gitea_headers)

# # Check if the mirror was set up successfully
# if response.status_code == 201:
#     print(f"Gitea repository '{repo_name}' set to mirror commits to GitHub repository successfully.")
# else:
#     print(f"Failed to set up mirror on Gitea repository. Status code: {response.status_code}")
#     print(response.text)

# # Set the repository name
# repo_name = args.repo_name

# # API endpoint for creating a repository
# url = f'https://api.github.com/user/repos'

# # JSON payload for the repository creation request
# payload = {
# 	'name': repo_name,
# 	'private': False,  # Set to True if you want a private repository
# 	# You can add more options like description, homepage, etc. if needed
# }

# # Headers containing the authorization token
# headers = {
# 	'Authorization': f'token {token}',
# 	'Accept': 'application/vnd.github.v3+json'
# }

# # Make POST request to create the repository
# response = requests.post(url, json=payload, headers=headers)

# # Check if the repository was created successfully
# if response.status_code == 201:
# 	print(f"Repository '{repo_name}' created successfully.")
# else:
# 	print(f"Failed to create repository. Status code: {response.status_code}")
# 	print(response.text)

