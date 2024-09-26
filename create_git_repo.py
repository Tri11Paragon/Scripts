#!/usr/bin/python3

import requests
import json
import argparse
import os
from pathlib import Path

class EnvData:
	def __init__(self, github_username = '', gitea_username = '', github_token = '', gitea_token = ''):
		self.github_token = github_token
		self.gitea_token = gitea_token
		self.github_username = github_username
		self.gitea_username = gitea_username
  
	def get_env_from_file(file):
		f = open(file, "rt")
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
			print("Failed to parse github token!")
		try:
			gitea_token = values["gitea_token"]
		except:
			print("Failed to parse gitea token!")
		try:
			github_username = values["github_username"]
		except:
			print("Failed to parse github username! Assuming you are me!")
			github_username = "Tri11Paragon"
		try:
			gitea_username = values["gitea_username"]
		except:
			print("Failed to parse gitea username! Assuming github username")
			gitea_username = github_username
		return EnvData(github_username=github_username, gitea_username=gitea_username, github_token=github_token, gitea_token=gitea_token)

class RepoData:
    def __init__(self, repo_name, description, env: EnvData, gitea_url = "https://git.tpgc.me"):
        self.repo_name = repo_name
        self.description = description
        self.env = env
        self.gitea_url = gitea_url

def get_env_from_os():
    return EnvData(github_username=os.environ["github_username"], gitea_username=os.environ["gitea_username"], github_token=os.environ["github_token"], gitea_token=os.environ["gitea_token"])

def create_repo(data: RepoData):
	# GitHub API endpoint for creating a repository
	github_url = f'https://api.github.com/user/repos'
	github_payload = {
		'name': data.repo_name,
		'description': data.description,
		'private': False  # Set to True if you want a private repository
	}
	github_headers = {
		'Authorization': f'token {data.env.github_token}',
		'Accept': 'application/vnd.github.v3+json'
	}

	# Create repository on GitHub
	response = requests.post(github_url, json=github_payload, headers=github_headers)
	if response.status_code == 201:
		print(f"GitHub repository '{data.repo_name}' created successfully.")
	else:
		print(f"Failed to create GitHub repository. Status code: {response.status_code}")
		print(response.text)
		return False

	# Gitea API endpoint for creating a repository
	gitea_url = f'{data.gitea_url}/api/v1/repos/migrate'
	gitea_payload = {
		'auth_token': data.env.github_token,
		'auth_username': data.env.github_username,
		'clone_addr': f'https://github.com/{data.env.github_username}/{data.repo_name}.git',
		'description': data.description,
		"issues": True,
		"labels": True,
		"lfs": False,
		"mirror": True,
		"mirror_interval": "1h",
		"pull_requests": True,
		"releases": True,
		"service": "github",
		"wiki": True,
		'repo_name': data.repo_name,
		'repo_owner': data.env.gitea_username,
		'private': False  # Set to True if you want a private repository
	}
	gitea_headers = {
		'Authorization': f'token {data.env.gitea_token}',
		'Accept': 'application/json',
		'Content-Type': 'application/json'
	}

	# Create repository on Gitea
	response = requests.post(gitea_url, json=gitea_payload, headers=gitea_headers)
	if response.status_code == 201:
		print(f"Gitea repository '{data.repo_name}' created successfully.")
		return True
	else:
		print(f"Failed to create Gitea repository. Status code: {response.status_code}")
		print(response.text)
		return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    prog='Repo Creator',
                    description='Create Git Repos on Gitea and Github',
                    epilog='Hello')
    parser.add_argument('repo_name')
    parser.add_argument('-e', help="environment file", required=False, default=str(Path.home() / ".brett_scripts.env"))
    parser.add_argument('-d', '--description', default = "")
    
    args = parser.parse_args()
    
    if (args.e is not None) and not (args.e == 'env'):
        env = EnvData.get_env_from_file(args.e)
    else:
        env = get_env_from_os()
    
    create_repo(RepoData(repo_name=args.repo_name, description=args.description, env=env))
    