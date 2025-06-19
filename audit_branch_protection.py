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

# 保護項目（クラシックプロテクション）
CLASSIC_PROTECTIONS = [
    ('プルリクエストレビューの必須', lambda p: bool(p.get('required_pull_request_reviews'))),
    ('管理者も含める', lambda p: bool(p.get('enforce_admins', {}).get('enabled'))),
    ('ステータスチェックの必須', lambda p: bool(p.get('required_status_checks'))),
    ('直線的な履歴の必須', lambda p: bool(p.get('required_linear_history', {}).get('enabled'))),
    ('強制プッシュの許可', lambda p: bool(p.get('allow_force_pushes', {}).get('enabled'))),
    ('削除の許可', lambda p: bool(p.get('allow_deletions', {}).get('enabled'))),
]

# 保護項目（ルールセット）
RULESET_PROTECTIONS = [
    ('作成の制限', lambda r: any(rule['type'] == 'creation' for rule in r.get('rules', []))),
    ('更新の制限', lambda r: any(rule['type'] == 'update' for rule in r.get('rules', []))),
    ('プルリクエストレビューの必須', lambda r: any(rule['type'] == 'pull_request_review' for rule in r.get('rules', []))),
    ('ステータスチェックの必須', lambda r: any(rule['type'] == 'required_status_checks' for rule in r.get('rules', []))),
    ('管理者も含める', lambda r: bool(r.get('bypass_actors'))),
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
    print(f"取得したリポジトリ: {repo_names}")

    # --- クラシックプロテクション（CSV）---
    classic_matrix = {prot[0]: {} for prot in CLASSIC_PROTECTIONS}
    classic_columns = []

    for repo in repo_names:
        prot = get_classic_protection(repo)
        col = (repo, BRANCH)
        classic_columns.append(col)
        for prot_name, check_fn in CLASSIC_PROTECTIONS:
            classic_matrix[prot_name][col] = 'y' if check_fn(prot) else 'n'

    # Shift-JISで書き出し
    with open('クラシック保護マトリックス.csv', 'w', newline='', encoding='shift_jis') as f:
        writer = csv.writer(f)
        writer.writerow(['保護項目'] + [col[0] for col in classic_columns])
        writer.writerow([''] + [col[1] for col in classic_columns])
        for prot_name in classic_matrix:
            row = [prot_name] + [classic_matrix[prot_name][col] for col in classic_columns]
            writer.writerow(row)
    print("クラシック保護マトリックスを書き出しました。")

    # --- ルールセット（CSV）---
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
                col = (repo, rs.get('name', 'ルールセット名なし'), BRANCH)
                ruleset_columns.append(col)
                for prot_name, check_fn in RULESET_PROTECTIONS:
                    ruleset_matrix[prot_name][col] = 'y' if check_fn(rs) else 'n'

    ruleset_columns = list(dict.fromkeys(ruleset_columns))

    with open('ルールセットマトリックス.csv', 'w', newline='', encoding='shift_jis') as f:
        writer = csv.writer(f)
        writer.writerow(['保護項目'] + [col[0] for col in ruleset_columns])
        writer.writerow([''] + [col[1] for col in ruleset_columns])   # ルールセット名
        writer.writerow([''] + [col[2] for col in ruleset_columns])   # ブランチ名
        for prot_name in ruleset_matrix:
            row = [prot_name] + [
                ruleset_matrix[prot_name].get(col, 'n') for col in ruleset_columns
            ]
            writer.writerow(row)
    print("ルールセットマトリックスを書き出しました。")

if __name__ == "__main__":
    main()
