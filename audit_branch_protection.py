import os
import requests
import csv

token = os.environ.get('GITHUB_TOKEN') #org内なので要らない
org = os.environ.get('ORG_NAME', 'test-for-my-prg') # orgのIDに変える
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

def get_classic_protection(repo, branch='main'):
    url = f"https://api.github.com/repos/{org}/{repo}/branches/{branch}/protection"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    return None

def summarize_classic(protection):
    checks = []
    if not protection:
        return ""
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
    return ", ".join(checks) if checks else ""

def get_rulesets(repo):
    url = f"https://api.github.com/repos/{org}/{repo}/rulesets"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return r.json()
    return []

def summarize_rulesets(rulesets, branch='main'):
    descriptions = []
    for rs in rulesets:
        # Rulesets can have various criteria—let's list their name/description
        applies = False
        targets = rs.get('target_branches', [])
        if targets:
            if branch in targets or 'all' in [t.lower() for t in targets]:
                applies = True
        elif rs.get('enforcement') != 'disabled':
            applies = True
        if applies:
            desc = rs.get('name', 'Unnamed Ruleset')
            branch_rules = []
            if rs.get('rules'):
                for rule in rs['rules']:
                    if rule['type'] == 'creation':
                        branch_rules.append('Restrict creations')
                    elif rule['type'] == 'update':
                        branch_rules.append('Restrict updates')
                    # You can expand this section for more rule types
            if branch_rules:
                descriptions.append(f"{desc}: " + ', '.join(branch_rules))
            else:
                descriptions.append(desc)
    return "; ".join(descriptions) if descriptions else ""

def main():
    with open('protection_audit.csv', 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['repo', 'branch', 'classic_protections', 'rulesets'])
        repos = get_repos()
        print("Repos found:", [repo['name'] for repo in repos])
        for repo in repos:
            repo_name = repo['name']
            classic = get_classic_protection(repo_name)
            rulesets = get_rulesets(repo_name)
            classic_summary = summarize_classic(classic)
            ruleset_summary = summarize_rulesets(rulesets)
            writer.writerow([
                repo_name,
                'main',
                classic_summary or "None",
                ruleset_summary or "None"
            ])
    print("CSV export complete.")

if __name__ == "__main__":
    main()
