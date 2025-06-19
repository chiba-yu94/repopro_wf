import os
import requests
import csv

ORG = os.environ.get('ORG_NAME', 'your-org-name')
BRANCH = os.environ.get('BRANCH', 'main')
TOKEN = os.environ['GITHUB_TOKEN']
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json"
}

# Protections to audit (expand as needed)
CLASSIC_PROTECTIONS = [
    ('Require PR review', lambda p: bool(p.get('required_pull_request_reviews'))),
    ('Include admins', lambda p: bool(p.get('enforce_admins', {}).get('enabled'))),
    ('Require status checks', lambda p: bool(p.get('required_status_checks'))),
    ('Require linear history', lambda p: bool(p.get('required_linear_history', {}).get('enabled'))),
    ('Force pushes allowed', lambda p: bool(p.get('allow_force_pushes', {}).get('enabled'))),
    ('Allow deletions', lambda p: bool(p.get('allow_deletions', {}).get('enabled'))),
]

RULESET_PROTECTIONS = [
    ('Restrict creations', lambda r: any(rule['type'] == 'creation' for rule in r.get('rules', []))),
    ('Restrict updates', lambda r: any(rule['type'] == 'update' for rule in r.get('rules', []))),
    ('Require PR review', lambda r: any(rule['type'] == 'pull_request_review' for rule in r.get('rules', []))),
    ('Require status checks', lambda r: any(rule['type'] == 'required_status_checks' for rule in r.get('rules', []))),
    ('Include admins', lambda r: bool(r.get('bypass_actors'))),
]

def get_repos():
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/orgs/{ORG}/repos?per_page=100&page={page}"
        r = requests.get(url, headers=HEADERS)
        data = r.json()
        if not data or 'message' in data:
            break
        repos.extend(data)
        if len(data) < 100:
            break
        page += 1
    return repos

def get_classic_protection(repo, branch=BRANCH):
    url = f"https://api.github.com/repos/{ORG}/{repo}/branches/{branch}/protection"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    return {}

def get_rulesets(repo):
    url = f"https://api.github.com/repos/{ORG}/{repo}/rulesets"
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    return []

def main():
    repos = get_repos()
    repo_names = [repo['name'] for repo in repos]
    print(f"Repos found: {repo_names}")

    # --- CLASSIC CSV ---
    classic_matrix = {prot[0]: {} for prot in CLASSIC_PROTECTIONS}
    classic_columns = []

    for repo in repo_names:
        prot = get_classic_protection(repo)
        col = (repo, BRANCH)
        classic_columns.append(col)
        for prot_name, check_fn in CLASSIC_PROTECTIONS:
            classic_matrix[prot_name][col] = 'y' if check_fn(prot) else 'n'

    # Write classic protections matrix CSV
    with open('classic_protections_matrix.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['protection'] + [col[0] for col in classic_columns])
        writer.writerow([''] + [col[1] for col in classic_columns])
        for prot_name in classic_matrix:
            row = [prot_name] + [classic_matrix[prot_name][col] for col in classic_columns]
            writer.writerow(row)
    print("Classic protections matrix exported.")

    # --- RULESET CSV ---
    ruleset_columns = []
    ruleset_matrix = {prot[0]: {} for prot in RULESET_PROTECTIONS}

    for repo in repo_names:
        rulesets = get_rulesets(repo)
        for rs in rulesets:
            targets = rs.get('target_branches', []) or []
            applies = False
            if not targets or BRANCH in targets or "all" in [t.lower() for t in targets]:
                applies = True
            elif any(BRANCH == t or t == "*" for t in targets):
                applies = True
            if rs.get('enforcement', 'active') == 'disabled':
                applies = False
            if applies:
                col = (repo, rs.get('name', 'unnamed'), BRANCH)
                ruleset_columns.append(col)
                for prot_name, check_fn in RULESET_PROTECTIONS:
                    ruleset_matrix[prot_name][col] = 'y' if check_fn(rs) else 'n'

    ruleset_columns = list(dict.fromkeys(ruleset_columns))

    with open('rulesets_matrix.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['protection'] + [col[0] for col in ruleset_columns])
        writer.writerow([''] + [col[1] for col in ruleset_columns])   # ruleset names
        writer.writerow([''] + [col[2] for col in ruleset_columns])   # branch names
        for prot_name in ruleset_matrix:
            row = [prot_name] + [
                ruleset_matrix[prot_name].get(col, 'n') for col in ruleset_columns
            ]
            writer.writerow(row)
    print("Rulesets matrix exported.")

if __name__ == "__main__":
    main()
