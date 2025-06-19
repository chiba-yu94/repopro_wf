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

# --- クラシック保護 項目 ---
CLASSIC_KEYS = [
    'プルリクエストのマージ前にレビューが必須',
    '必須レビュー数',
    'ステータスチェックの必須',
    '必須ステータスチェック名',
    '直線的な履歴の必須',
    'サイン済みコミット必須',
    '強制プッシュの許可',
    '削除の許可',
    '管理者も含める',
    '必須デプロイメント環境',
]

# --- ルールセット 項目 ---
RULESET_KEYS = [
    '作成の制限',
    '更新の制限',
    '削除の制限',
    '直線的な履歴の必須',
    'マージキュー必須',
    'マージキュー: メソッド',
    'マージキュー: 同時ビルド数',
    'マージキュー: 最小グループ数',
    'マージキュー: 最大グループ数',
    'マージキュー: 最小グループ待機分',
    'マージキュー: 全てのエントリが必須チェック合格',
    'マージキュー: ステータスチェックタイムアウト',
    'デプロイメント必須',
    'サイン済みコミット必須',
    'プルリクエストのマージ前に必須',
    '必須レビュー数',
    'ステータスチェックの必須',
    '必須ステータスチェック名',
    '強制プッシュのブロック',
    'コードスキャン結果制限',
    'バイパスアクター'
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
    columns = []
    matrix = {k: {} for k in CLASSIC_KEYS}
    for repo in repos:
        prot = get_classic_protection(repo, branch)
        col = (repo, branch)
        columns.append(col)
        for key in CLASSIC_KEYS:
            matrix[key][col] = 'NA'
        if prot:
            matrix['プルリクエストのマージ前にレビューが必須'][col] = 'y' if prot.get('required_pull_request_reviews') else 'n'
            pr_reviews = prot.get('required_pull_request_reviews', {})
            matrix['必須レビュー数'][col] = pr_reviews.get('required_approving_review_count', 'NA') if pr_reviews else 'NA'
            matrix['ステータスチェックの必須'][col] = 'y' if prot.get('required_status_checks') else 'n'
            status_checks = prot.get('required_status_checks', {}).get('checks', [])
            matrix['必須ステータスチェック名'][col] = ','.join([sc['context'] for sc in status_checks]) if status_checks else 'NA'
            matrix['直線的な履歴の必須'][col] = 'y' if prot.get('required_linear_history', {}).get('enabled') else 'n'
            matrix['サイン済みコミット必須'][col] = 'y' if prot.get('required_signatures', {}).get('enabled') else 'n'
            matrix['強制プッシュの許可'][col] = 'y' if prot.get('allow_force_pushes', {}).get('enabled') else 'n'
            matrix['削除の許可'][col] = 'y' if prot.get('allow_deletions', {}).get('enabled') else 'n'
            matrix['管理者も含める'][col] = 'y' if prot.get('enforce_admins', {}).get('enabled') else 'n'
            deployments = prot.get('required_deployments', {}).get('environments', [])
            matrix['必須デプロイメント環境'][col] = ','.join(deployments) if deployments else 'NA'
    return columns, matrix

def extract_ruleset_matrix(repos, branch):
    columns = []
    matrix = {k: {} for k in RULESET_KEYS}
    for repo in repos:
        rulesets = get_rulesets(repo)
        if rulesets:
            for rs in rulesets:
                rs_name = rs.get('name', 'ルールセット')
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
                for key in RULESET_KEYS:
                    matrix[key][col] = 'NA'
                for rule in rs.get('rules', []):
                    rule_type = rule.get('type', '')
                    conf = rule.get('configuration', {})
                    if rule_type == 'creation':
                        matrix['作成の制限'][col] = 'y'
                    if rule_type == 'update':
                        matrix['更新の制限'][col] = 'y'
                    if rule_type == 'deletion':
                        matrix['削除の制限'][col] = 'y'
                    if rule_type == 'required_linear_history':
                        matrix['直線的な履歴の必須'][col] = 'y'
                    if rule_type == 'merge_queue':
                        matrix['マージキュー必須'][col] = 'y'
                        matrix['マージキュー: メソッド'][col] = conf.get('merge_method', 'NA')
                        matrix['マージキュー: 同時ビルド数'][col] = conf.get('build_concurrency', 'NA')
                        matrix['マージキュー: 最小グループ数'][col] = conf.get('min_group_size', 'NA')
                        matrix['マージキュー: 最大グループ数'][col] = conf.get('max_group_size', 'NA')
                        matrix['マージキュー: 最小グループ待機分'][col] = conf.get('wait_time_to_meet_min_group_size', 'NA')
                        matrix['マージキュー: 全てのエントリが必須チェック合格'][col] = (
                            'y' if conf.get('require_all_group_entries_to_pass', False) else 'n'
                        ) if conf else 'NA'
                        matrix['マージキュー: ステータスチェックタイムアウト'][col] = conf.get('status_check_timeout', 'NA')
                    if rule_type == 'required_deployments':
                        matrix['デプロイメント必須'][col] = 'y'
                    if rule_type == 'signed_commits':
                        matrix['サイン済みコミット必須'][col] = 'y'
                    if rule_type == 'pull_request':
                        matrix['プルリクエストのマージ前に必須'][col] = 'y'
                        matrix['必須レビュー数'][col] = conf.get('required_approving_review_count', 'NA')
                    if rule_type == 'required_status_checks':
                        matrix['ステータスチェックの必須'][col] = 'y'
                        checks = conf.get('required_status_checks', [])
                        matrix['必須ステータスチェック名'][col] = ','.join(checks) if checks else 'NA'
                    if rule_type == 'block_force_pushes':
                        matrix['強制プッシュのブロック'][col] = 'y'
                    if rule_type == 'code_scanning_results':
                        matrix['コードスキャン結果制限'][col] = 'y'
                if 'bypass_actors' in rs:
                    actors = rs.get('bypass_actors', [])
                    matrix['バイパスアクター'][col] = ','.join([a.get('actor_id', '') for a in actors]) if actors else 'NA'
        else:
            col = (repo, '(ルールセットなし)', branch)
            columns.append(col)
            for key in RULESET_KEYS:
                matrix[key][col] = 'NA'
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
