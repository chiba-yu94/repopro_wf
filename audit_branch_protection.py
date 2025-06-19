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

def extract_classic_row(repo, prot, branch):
    # 各値を'n'で初期化し、存在すれば値を埋める
    row = {
        'リポジトリ': repo,
        'ブランチ': branch,
    }
    row.update({k: 'n' for k in CLASSIC_KEYS})

    # 各キーの抽出
    if prot:
        row['プルリクエストレビューの必須'] = 'y' if prot.get('required_pull_request_reviews') else 'n'
        row['管理者も含める'] = 'y' if prot.get('enforce_admins', {}).get('enabled') else 'n'
        row['ステータスチェックの必須'] = 'y' if prot.get('required_status_checks') else 'n'
        row['直線的な履歴の必須'] = 'y' if prot.get('required_linear_history', {}).get('enabled') else 'n'
        row['強制プッシュの許可'] = 'y' if prot.get('allow_force_pushes', {}).get('enabled') else 'n'
        row['削除の許可'] = 'y' if prot.get('allow_deletions', {}).get('enabled') else 'n'
        # 詳細値
        pr_reviews = prot.get('required_pull_request_reviews', {})
        row['必要なレビュー数'] = pr_reviews.get('required_approving_review_count', 'n') if pr_reviews else 'n'
        status_checks = prot.get('required_status_checks', {}).get('checks', [])
        row['必須ステータスチェック名'] = ','.join([sc['context'] for sc in status_checks]) if status_checks else 'n'
    return row

def extract_ruleset_rows(repo, rulesets, branch):
    rows = []
    # rulesetごとに全項目'n'で初期化し、ヒットしたものだけ値を埋める
    if not rulesets:
        # ルールセット自体がない場合
        row = {'リポジトリ': repo, 'ルールセット名': '(なし)', 'ブランチ': branch}
        row.update({k: 'n' for k in RULESET_KEYS})
        rows.append(row)
        return rows

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
        row = {'リポジトリ': repo, 'ルールセット名': rs_name, 'ブランチ': branch}
        row.update({k: 'n' for k in RULESET_KEYS})

        # ルールセット内容から値抽出
        for rule in rs.get('rules', []):
            rule_type = rule.get('type', '')
            if rule_type == 'pull_request_review':
                row['プルリクエストレビューの必須'] = 'y'
                cnt = rule.get('configuration', {}).get('required_approving_review_count', 'n')
                row['必要なレビュー数'] = cnt
            elif rule_type == 'required_status_checks':
                row['ステータスチェックの必須'] = 'y'
                checks = rule.get('configuration', {}).get('required_status_checks', [])
                row['必須ステータスチェック名'] = ','.join(checks) if checks else 'n'
            elif rule_type == 'creation':
                row['作成の制限'] = 'y'
            elif rule_type == 'update':
                row['更新の制限'] = 'y'
            elif rule_type == 'deletion':
                row['削除の制限'] = 'y'
            # バイパスアクター例（管理者など）
            if 'bypass_actors' in rs:
                actors = rs.get('bypass_actors', [])
                row['バイパスアクター'] = ','.join([a.get('actor_id', '') for a in actors]) if actors else 'n'
        rows.append(row)
    return rows

def main():
    repos = get_repos()
    repo_names = [repo['name'] for repo in repos]
    print(f"取得したリポジトリ: {repo_names}")

    # --- クラシック保護 ---
    classic_rows = []
    for repo in repo_names:
        prot = get_classic_protection(repo)
        row = extract_classic_row(repo, prot, BRANCH)
        classic_rows.append(row)

    with open('クラシック保護一覧.csv', 'w', newline='', encoding='shift_jis') as f:
        writer = csv.DictWriter(f, fieldnames=['リポジトリ', 'ブランチ'] + CLASSIC_KEYS)
        writer.writeheader()
        for row in classic_rows:
            writer.writerow(row)
    print("クラシック保護一覧を書き出しました。")

    # --- ルールセット ---
    ruleset_rows = []
    for repo in repo_names:
        rulesets = get_rulesets(repo)
        rs_rows = extract_ruleset_rows(repo, rulesets, BRANCH)
        ruleset_rows.extend(rs_rows)

    with open('ルールセット一覧.csv', 'w', newline='', encoding='shift_jis') as f:
        writer = csv.DictWriter(f, fieldnames=['リポジトリ', 'ルールセット名', 'ブランチ'] + RULESET_KEYS)
        writer.writeheader()
        for row in ruleset_rows:
            writer.writerow(row)
    print("ルールセット一覧を書き出しました。")

if __name__ == "__main__":
    main()
