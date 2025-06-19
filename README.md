# GitHub リポジトリ保護設定監査ワークフロー

## 概要

GitHub組織内の全リポジトリについて  
- ブランチ保護（クラシックルール）
- ルールセット（Rulesets）

の有効状態を自動取得し、CSVとして一覧化します。

---

## 準備手順

### 1. PAT（Personal Access Token）の発行

1. [GitHubの設定ページ](https://github.com/settings/tokens)で「Tokens (classic)」を選択
2. `repo`スコープでトークン発行・コピー

### 2. PATをリポジトリのシークレットに登録

- `Settings → Secrets and variables → Actions → New repository secret`
    - Name: `MY_PAT`
    - Value: 発行したPAT

### 3. Actions 権限設定

- 組織・リポジトリともに  
    - Actions permissions: `Allow all actions and reusable workflows`
    - Workflow permissions: `Read and write permissions`

---

## 使い方

### 1. ファイル設置

- `audit_branch_protection.py`
- `.github/workflows/branch_protection_audit.yml`

### 2. ワークフロー実行

1. GitHub「Actions」タブへ
2. 「Branch Protection Audit」を選択
3. 「Run workflow」ボタンからブランチ名（例: `main`）を入力して実行

### 3. 結果取得

- 実行完了後、Actions詳細ページ上部の「Artifacts」より  
    - `クラシック保護マトリックス.csv`
    - `ルールセットマトリックス.csv`  
  をダウンロード

---

## CSV内容

- **クラシック保護マトリックス.csv**  
    - 各リポジトリ・ブランチごとのクラシック保護設定（y/n表示）
- **ルールセットマトリックス.csv**  
    - 各リポジトリ・ルールセット・ブランチごとのルールセット設定（y/n表示）

---

## 注意事項

- 日本語CSVはShift-JIS形式（Excelで文字化けしません）
- PATは外部に漏洩しないようご注意ください
- ルールセットはTeamプラン以上でプライベートリポジトリに適用されます
