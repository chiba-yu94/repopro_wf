import os
import requests
import CSV

# Get environment variables from GitHub Actions
token = os.environ.get('GITHUB_TOKEN')
org = os.environ.get('ORG_NAME', 'your-org-name')  # Replace as needed

headers = {
    "Authorization": f"token {token}",
    "Accept": "application/vnd.github+json"
}

def get_repos():
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{org}/repos?per_page=100&page={page}"
        r = requests.get(url, headers=headers)
        data = r.json()
        if not data or 'message' in data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos

def get_branch_protection(repo, branch='main'):
    url = f"https://api.github.com/repos/{org}/{repo}/branches/{branch}/protection"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    return None

def summarize_protection(protection):
    checks = []
    if protection.get('required_status_checks'):
        checks.append("Require status checks")
    if protection.get('required_pull_request_reviews'):
        checks.append("Require PR reviews")
    if protection.get('enforce_admins', {}).get('enabled'):
        checks.append("Include admins")
    if protection.get('required_linear_history', {}).get('enabled'):
        checks.append("Linear history")
    if protection.get('allow_force_pushes', {}).get('enabled'):
        checks.append("Force pushes allowed")
    if protection.get('allow_deletions', {}).get('enabled'):
        checks.append("Allow deletions")
    return ", ".join(checks) if checks else "No protections"

import csv

def main():
    with open('protection_audit.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['repo', 'branch', 'protections'])
        repos = get_repos()
        for repo in repos:
            repo_name = repo['name']
            protection = get_branch_protection(repo_name)
            summary = summarize_protection(protection) if protection else "No protections"
            writer.writerow([repo_name, 'main', summary])
    print("CSV export complete.")


if __name__ == "__main__":
    main()
