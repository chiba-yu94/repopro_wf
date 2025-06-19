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

def extract_ruleset_rule_details(repo, rs, branch):
    rows = []
    rs_name = rs.get('name', 'ルールセット名なし')
    targets = rs.get('target_branches', []) or []
    applies = False
    if not targets or branch in targets or "all" in [t.lower() for t in targets]:
        applies = True
    elif any(branch == t or t == "*" for t in targets):
        applies = True
    if rs.get('enforcement', 'active') == 'disabled':
        applies = False
    if not applies:
        return rows
    for rule in rs.get('rules', []):
        rule_type = rule.get('type', '')
        detail = ""
        # PRレビュー
        if rule_type == 'pull_request_review':
            cnt = rule.get('configuration', {}).get('required_approving_review_count', '未設定')
            detail = f"必要なレビュー数: {cnt}"
        # ステータスチェック
        elif rule_type == 'required_status_checks':
            checks = rule.get('configuration', {}).get('required_status_checks', [])
            detail = "チェック名: " + (",".join(checks) if checks else "なし")
        # 作成・更新・削除制限
        elif rule_type in ('creation', 'update', 'deletion'):
            actors = rule.get('actors', [])
            actor_names = ",".join(a.get('actor_id', '') for a in actors) if actors else "なし"
            detail = f"アクター: {actor_names}"
        else:
            detail = str(rule.get('configuration', {}))  # その他type
        rows.append([repo, rs_name, branch, rule_type, detail])
    return rows

def main():
    repos = get_repos()
    repo_names = [repo['name'] for repo in repos]
    print(f"取得したリポジトリ: {repo_names}")

    # --- クラシック保護マトリックス（既存のマトリックス形式） ---
    classic_matrix = {prot[0]: {} for prot in CLASSIC_PROTECTIONS}
    classic_columns = []

    for repo in repo_names:
        prot = get_classic_protection(repo)
        col = (repo, BRANCH)
        classic_columns.append(col)
        for prot_name, check_fn in CLASSIC_PROTECTIONS:
            classic_matrix[prot_name][col] = 'y' if check_fn(prot) else 'n'

    with open('クラシック保護マトリックス.csv', 'w', newline='', encoding='shift_jis') as f:
        writer = csv.writer(f)
        writer.writerow(['保護項目'] + [col[0] for col in classic_columns])
        writer.writerow([''] + [col[1] for col in classic_columns])
        for prot_name in classic_matrix:
            row = [prot_name] + [classic_matrix[prot_name][col] for col in classic_columns]
            writer.writerow(row)
    print("クラシック保護マトリックスを書き出しました。")

    # --- ルールセット個別ルール（詳細）CSV ---
    ruleset_detail_rows = []
    for repo in repo_names:
        rulesets = get_rulesets(repo)
        for rs in rulesets:
            ruleset_detail_rows.extend(extract_ruleset_rule_details(repo, rs, BRANCH))

    with open('ルールセット個別詳細.csv', 'w', newline='', encoding='shift_jis') as f:
        writer = csv.writer(f)
        writer.writerow(['リポジトリ', 'ルールセット名', 'ブランチ', 'ルールtype', '詳細内容'])
        for row in ruleset_detail_rows:
            writer.writerow(row)
    print("ルールセット個別詳細を書き出しました。")

if __name__ == "__main__":
    main()
