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

# 固定項目リスト：クラシック
CLASSIC_KEYS = [
    'プルリクエストレビューの必須',
    '管理者も含める',
    'ステータスチェックの必須',
    '直線的な履歴の必須',
    '強制プッシュの許可',
    '削除の許可',
    '必要なレビュー数',
    '必須ステータスチェック名'
]

# 固定項目リスト：ルールセット
RULESET_KEYS = [
    '作成の制限',
    '更新の制限',
    '削除の制限',
    'プルリクエストレビューの必須',
    '必要なレビュー数',
    'ステータスチェックの必須',
    '必須ステータスチェック名',
    'バイパスアクター',
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

def extract_classic_matrix(repos, branch):
    # 列ごと（repo, branch）で全項目をy/nで埋める
    columns = []
    matrix = {k: {} for k in CLASSIC_KEYS}
    for repo in repos:
        prot = get_classic_protection(repo, branch)
        col = (repo, branch)
        columns.append(col)
        # デフォルトn
        for key in CLASSIC_KEYS:
            matrix[key][col] = 'n'
        # 実値埋め
        if prot:
            matrix['プルリクエストレビューの必須'][col] = 'y' if prot.get('required_pull_request_reviews') else 'n'
            matrix['管理者も含める'][col] = 'y' if prot.get('enforce_admins', {}).get('enabled') else 'n'
            matrix['ステータスチェックの必須'][col] = 'y' if prot.get('required_status_checks') else 'n'
            matrix['直線的な履歴の必須'][col] = 'y' if prot.get('required_linear_history', {}).get('enabled') else 'n'
            matrix['強制プッシュの許可'][col] = 'y' if prot.get('allow_force_pushes', {}).get('enabled') else 'n'
            matrix['削除の許可'][col] = 'y' if prot.get('allow_deletions', {}).get('enabled') else 'n'
            pr_reviews = prot.get('required_pull_request_reviews', {})
            matrix['必要なレビュー数'][col] = pr_reviews.get('required_approving_review_count', 'n') if pr_reviews else 'n'
            status_checks = prot.get('required_status_checks', {}).get('checks', [])
            matrix['必須ステータスチェック名'][col] = ','.join([sc['context'] for sc in status_checks]) if status_checks else 'n'
    return columns, matrix

def extract_ruleset_matrix(repos, branch):
    columns = []
    matrix = {k: {} for k in RULESET_KEYS}
    for repo in repos:
        rulesets = get_rulesets(repo)
        if rulesets:
            for rs in rulesets:
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
                    continue
                col = (repo, rs_name, branch)
                columns.append(col)
                # デフォルトn
                for key in RULESET_KEYS:
                    matrix[key][col] = 'n'
                # 実値埋め
                for rule in rs.get('rules', []):
                    rule_type = rule.get('type', '')
                    if rule_type == 'pull_request_review':
                        matrix['プルリクエストレビューの必須'][col] = 'y'
                        cnt = rule.get('configuration', {}).get('required_approving_review_count', 'n')
                        matrix['必要なレビュー数'][col] = cnt
                    elif rule_type == 'required_status_checks':
                        matrix['ステータスチェックの必須'][col] = 'y'
                        checks = rule.get('configuration', {}).get('required_status_checks', [])
                        matrix['必須ステータスチェック名'][col] = ','.join(checks) if checks else 'n'
                    elif rule_type == 'creation':
                        matrix['作成の制限'][col] = 'y'
                    elif rule_type == 'update':
                        matrix['更新の制限'][col] = 'y'
                    elif rule_type == 'deletion':
                        matrix['削除の制限'][col] = 'y'
                    if 'bypass_actors' in rs:
                        actors = rs.get('bypass_actors', [])
                        matrix['バイパスアクター'][col] = ','.join([a.get('actor_id', '') for a in actors]) if actors else 'n'
        else:
            # ルールセット自体なしの場合
            col = (repo, '(ルールセットなし)', branch)
            columns.append(col)
            for key in RULESET_KEYS:
                matrix[key][col] = 'n'
    return columns, matrix

def main():
    repos = get_repos()
    repo_names = [repo['name'] for repo in repos]
    print(f"取得したリポジトリ: {repo_names}")

    # --- クラシック保護マトリクス ---
    columns, matrix = extract_classic_matrix(repo_names, BRANCH)
    with open('クラシック保護マトリクス.csv', 'w', newline='', encoding='shift_jis') as f:
        writer = csv.writer(f)
        writer.writerow(['保護項目'] + [col[0] for col in columns])
        writer.writerow([''] + [col[1] for col in columns])
        for key in CLASSIC_KEYS:
            row = [key] + [matrix[key][col] for col in columns]
            writer.writerow(row)
    print("クラシック保護マトリクスを書き出しました。")

    # --- ルールセットマトリクス ---
    rs_columns, rs_matrix = extract_ruleset_matrix(repo_names, BRANCH)
    with open('ルールセットマトリクス.csv', 'w', newline='', encoding='shift_jis') as f:
        writer = csv.writer(f)
        writer.writerow(['保護項目'] + [col[0] for col in rs_columns])
        writer.writerow([''] + [col[1] for col in rs_columns])   # ルールセット名
        writer.writerow([''] + [col[2] for col in rs_columns])   # ブランチ名
        for key in RULESET_KEYS:
            row = [key] + [rs_matrix[key][col] for col in rs_columns]
            writer.writerow(row)
    print("ルールセットマトリクスを書き出しました。")

if __name__ == "__main__":
    main()
