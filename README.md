# DefenderForDevOps SecurePipeline Training

Azure DevOps Pipelines を使った DevSecOps（セキュア CI/CD）の基本を学ぶための教材です。意図的に脆弱性を埋め込んだ Flask Web アプリケーションを題材に、ビルド・単体テスト・各種セキュリティスキャン・コンテナビルド・デプロイを通すパイプラインを構築し、実際にスキャン結果を確認したうえで脆弱性を修正する一連の流れを体験します。

OSS スキャナ（Bandit / Semgrep / Gitleaks / pip-audit / Trivy / OWASP ZAP）は追加ライセンスなしで常時実行します。CodeQL（GitHub Advanced Security for Azure DevOps の機能）と Microsoft Security DevOps（Microsoft Defender for Cloud 連携）は有償ライセンスが前提のため、フラグで任意に有効化してください。

> ⚠️ **教育目的の教材です。アプリケーションは意図的に脆弱性を含みます。本番環境では使用しないでください。**

## 前提条件

| 項目 | 内容 | ライセンス |
|------|------|-----------|
| Azure DevOps 組織 / プロジェクト | パイプライン実行環境 | 無料枠で可 |
| Microsoft-hosted agent (`ubuntu-latest`) | パイプライン実行エージェント | 無料枠 / 並列ジョブ |
| [SARIF SAST Scans Tab](https://marketplace.visualstudio.com/items?itemName=sariftools.scans) 拡張 | Scans タブで SARIF 結果を表示 | 無料 |
| CodeQL（任意） | GitHub Advanced Security for Azure DevOps の機能 | 有償 |
| Microsoft Security DevOps（任意） | Microsoft Defender for Cloud との連携 | 有償（Microsoft Defender Cloud Security Posture Management） |

### 必要な権限とロール

各作業に必要なロールと、そのロールが属するレイヤ（管理基盤）は以下のとおりです。Azure DevOps のロール（セキュリティグループ）と、Azure RBAC ・ Microsoft Entra ID のロールは別のレイヤです。混同しないでください。

| 作業 | 必要なロール | ロールが属するレイヤ | 補足 |
|------|------------|------------------|------|
| SARIF SAST Scans Tab 拡張のインストール | **Project Collection Administrators** グループのメンバー（または組織 Owner） | Azure DevOps（組織レベル） | Microsoft Entra ID のロールでも Azure RBAC のロールでもない。権限がない一般ユーザーは拡張を「リクエスト」し、上記管理者が承認・インストールする |
| パイプラインの作成・実行 | **Contributors** グループのメンバー | Azure DevOps（プロジェクトレベル） | 通常のプロジェクトメンバーで可 |
| CodeQL（GitHub Advanced Security for Azure DevOps）の有効化 | **Project Administrators** グループのメンバー | Azure DevOps（プロジェクトレベル） | 課金の有効化には組織 Owner が必要 |
| Microsoft Security DevOps（Microsoft Defender for Cloud 連携） | Azure サブスクリプションの **Owner** または **Security Admin**＋Azure DevOps の **Project Collection Administrators** | Azure RBAC（サブスクリプションレベル）＋Azure DevOps（組織レベル） | 連携手順は [`docs/DEFENDER-INTEGRATION.md`](./docs/DEFENDER-INTEGRATION.md) |
| Azure へのデプロイ（ACR / Web App for Containers）の準備 | リソース作成: サブスクリプションまたはリソースグループの **Owner** / **Contributor**＋RBAC 付与に **User Access Administrator** または **Owner**。サービス接続作成: Azure DevOps の **Endpoint Administrator**（または **Project Administrators**） | Azure RBAC（サブスクリプション／リソースグループレベル）＋Azure DevOps（プロジェクトレベル） | 手順は [`docs/AZURE-SETUP.md`](./docs/AZURE-SETUP.md) |

> ロールの名称と付与手順は変更される可能性があります。最新情報は公式ドキュメントを参照してください。

## 構成ファイル

| パス | 種別 | 用途 |
|------|------|------|
| [`azure-pipelines.yml`](./azure-pipelines.yml) | Pipeline | CI/CD パイプライン定義（ビルド・テスト・スキャン・デプロイ） |
| [`app/app.py`](./app/app.py) | Python | 脆弱性を含む Flask アプリケーション本体 |
| [`app/templates/`](./app/templates/) | HTML | 画面テンプレート（index / login / profile） |
| [`app/requirements.txt`](./app/requirements.txt) | Python | 依存ライブラリ（意図的に旧バージョン） |
| [`app/Dockerfile`](./app/Dockerfile) | Docker | コンテナイメージ定義 |
| [`tests/test_app.py`](./tests/test_app.py) | pytest | 機能ユニットテスト（修正後の回帰確認用） |
| [`tools/pipaudit_to_sarif.py`](./tools/pipaudit_to_sarif.py) | Python | pip-audit JSON → SARIF 変換ツール |
| [`docs/LAB-GUIDE.md`](./docs/LAB-GUIDE.md) | Markdown | 演習ガイド（結果確認場所・脆弱性発見手順） |
| [`docs/AZURE-SETUP.md`](./docs/AZURE-SETUP.md) | Markdown | Azure デプロイ事前準備ガイド（GUI 操作手順・値の反映先） |
| [`docs/SOLUTION.md`](./docs/SOLUTION.md) | Markdown | 脆弱性の修正方法（解答） |
| [`docs/DEFENDER-INTEGRATION.md`](./docs/DEFENDER-INTEGRATION.md) | Markdown | Defender for Cloud 連携手順 |

## パイプラインのデータフロー

```text
Build ─▶ Test ─┬─▶ SAST (Bandit + Semgrep) ─┐
               ├─▶ SCA (pip-audit)          ├─▶ DockerBuild ─▶ Trivy ─▶ PublishScans ─▶ Deploy
               ├─▶ Secret (Gitleaks)        ┘
               │
               ├─▶ DAST (OWASP ZAP)            （独立: Artifacts に HTML レポート）
               ├─▶ CodeQL                      （任意: USE_CODEQL=true / GitHub Advanced Security for Azure DevOps）
               └─▶ Microsoft Security DevOps   （任意: USE_DEFENDER_FOR_DEVOPS=true）

SARIF（Bandit / Semgrep / Gitleaks / pip-audit / Trivy）
  → CodeAnalysisLogs アーティファクト → Scans タブで一覧表示
```

## 展開手順

1. 本フォルダの内容を Azure DevOps の Git リポジトリにプッシュします。
2. Azure DevOps 組織に [SARIF SAST Scans Tab](https://marketplace.visualstudio.com/items?itemName=sariftools.scans) 拡張をインストールします。この作業は Azure DevOps 組織の **Project Collection Administrators** グループのメンバーが行います（詳細は上記「必要な権限とロール」を参照）。
3. **Pipelines** > **New pipeline** > **Azure Repos Git** を選択し、リポジトリの [`azure-pipelines.yml`](./azure-pipelines.yml) を指定します。
4. パイプラインを実行します。
5. 実行完了後、各結果を確認します（詳細は [`docs/LAB-GUIDE.md`](./docs/LAB-GUIDE.md)）。
   - **Scans** タブ: SAST / SCA / Secret / Container の SARIF 結果
   - **Tests** タブ: pytest の結果
   - **Artifacts**（`zap-report`）: OWASP ZAP の DAST レポート（HTML）

> パイプライン作成・拡張インストールの最新手順は、変更される可能性があります。最新手順は公式ドキュメントを参照してください。
> - [Create your first pipeline](https://learn.microsoft.com/azure/devops/pipelines/create-first-pipeline)
> - [Install extensions](https://learn.microsoft.com/azure/devops/marketplace/install-extension)

## アプリケーションへのアクセス

パイプラインの `Deploy` ステージは、ビルドしたコンテナイメージを **Azure Container Registry** にプッシュし、**Azure Web App for Containers** にデプロイします。デプロイ後は Web App の URL `https://<webAppName>.azurewebsites.net` でアプリにアクセスでき、脆弱性の手動確認（XSS・アクセスコントロール・Cookie など）もその URL 上で行えます。

> **ACR や Web App などの Azure リソースはパイプラインでは自動作成されません。** リソースの作成、サービス接続・RBAC の設定、そして作成した値をパイプライン変数のどこに反映するかの詳細な GUI 操作手順は **[`docs/AZURE-SETUP.md`](./docs/AZURE-SETUP.md)** を参照してください。

### 概要（詳細は事前準備ガイド）

1. [`docs/AZURE-SETUP.md`](./docs/AZURE-SETUP.md) に従って Azure リソース（ACR / Web App for Containers）と Azure DevOps のサービス接続を作成し、サービスプリンシパルに **AcrPush** と **Contributor** を付与します。
2. 控えた値を [`azure-pipelines.yml`](./azure-pipelines.yml) の `variables` に反映します。

   | 控えた値 | パイプライン変数 | 例 |
   |-----------|----------------|----|
   | Container Registry のログインサーバー | `acrLoginServer` | `acrdevsecopstraining.azurecr.io` |
   | Web アプリの名前 | `webAppName` | `app-devsecops-training` |
   | サービス接続の名前 | `azureServiceConnection` | `sc-devsecops-training` |
   | デプロイ有効化 | `DEPLOY_TO_AZURE` | `true` |

3. パイプラインを実行します。`Deploy` ステージが ACR へのプッシュと Web App へのデプロイを行います。
4. デプロイ後、`https://<webAppName>.azurewebsites.net` にアクセスします。

> `DEPLOY_TO_AZURE` が `true` でない場合、`Deploy` ステージはデプロイを行わずスキップ用のメッセージを表示して終了します（ビルドとスキャンは引き続き実行されます）。

### デプロイ後の主な画面

| URL | 内容 |
|-----|------|
| `https://<webAppName>.azurewebsites.net/` | トップページ |
| `https://<webAppName>.azurewebsites.net/login` | ログイン（`alice` / `alice-password`、`bob` / `bob-password`） |
| `https://<webAppName>.azurewebsites.net/profile/1` | プロフィール（アクセスコントロールの脆弱性の確認に使用） |
| `https://<webAppName>.azurewebsites.net/search?q=test` | 検索（クロスサイトスクリプティングの確認に使用） |

### ローカルでの起動（任意）

Azure 環境を使わずに手元で動作確認する場合は、Docker が動作する PC でリポジトリのルートから次を実行します。

```bash
docker build -t training-app ./app
docker run -d --name training-app -p 5000:5000 training-app
# 確認後: docker rm -f training-app
```

ブラウザで `http://localhost:5000` を開きます。

## 技術仕様

### 任意フラグ

| 変数 | 既定値 | 説明 |
|------|--------|------|
| `USE_CODEQL` | `false` | `true` で CodeQL ステージを実行（GitHub Advanced Security for Azure DevOps のライセンス必須） |
| `USE_DEFENDER_FOR_DEVOPS` | `false` | `true` で Microsoft Security DevOps ステージを実行（Microsoft Defender Cloud Security Posture Management 必須） |

#### 任意フラグの変更方法

CodeQL と Microsoft Security DevOps は既定で無効です。有効化するには次のいずれかの方法でフラグを `true` にします。

**方法 1: YAML を直接編集する（推奨・確実）**

[`azure-pipelines.yml`](./azure-pipelines.yml) の `variables` ブロックを書き換えてコミットします。

```yaml
variables:
  - name: USE_CODEQL
    value: 'true'              # false -> true に変更
  - name: USE_DEFENDER_FOR_DEVOPS
    value: 'true'              # false -> true に変更
```

**方法 2: 実行時に上書きする**

パイプライン画面で **Run pipeline** > **Variables**（または **Advanced options**）を開き、同名の変数 `USE_CODEQL` / `USE_DEFENDER_FOR_DEVOPS` に `true` を指定して実行します。1 回限りの実行で有効化したい場合に使います。

いずれの方法でも、対応する拡張・ライセンスが未導入の場合は該当ステージはプレースホルダのまま終了します（詳細は [`azure-pipelines.yml`](./azure-pipelines.yml) 内コメントおよび [`docs/DEFENDER-INTEGRATION.md`](./docs/DEFENDER-INTEGRATION.md) を参照）。

### スキャン結果の確認場所

| ツール | 種別 | 確認場所 |
|--------|------|---------|
| Bandit / Semgrep | SAST | Scans タブ |
| pip-audit | SCA | Scans タブ |
| Gitleaks | Secret | Scans タブ |
| Trivy | Container | Scans タブ |
| OWASP ZAP | DAST | Artifacts（`zap-report` の HTML レポート） |
| CodeQL | SAST | Advanced Security > Code scanning alerts |
| Microsoft Security DevOps | 集約 | Microsoft Defender for Cloud > DevOps security |

## 含まれる脆弱性

| # | 脆弱性 | 該当箇所 |
|---|--------|---------|
| 1 | ハードコードされた認証情報（ダミー） | [`app/app.py`](./app/app.py) の `SECRET_KEY` / `DB_PASSWORD` / AWS キー |
| 2 | HttpOnly のない Cookie | `/login` の `set_cookie(httponly=False)` |
| 3 | 古い脆弱なライブラリ | [`app/requirements.txt`](./app/requirements.txt)（Flask 2.0.1 等） |
| 4 | クロスサイトスクリプティング（XSS） | `/search` の `render_template_string` |
| 5 | アクセスコントロールの脆弱性（IDOR） | `/profile/<user_id>` の認可チェック欠落 |

修正方法は [`docs/SOLUTION.md`](./docs/SOLUTION.md) を参照してください。

## 注意事項

- 本教材は公式 Microsoft 製品ではなく、DevSecOps を学習するためのサンプルです。
- アプリケーションは意図的に脆弱性を含みます。**ローカルまたは隔離された検証環境でのみ実行してください。**
- 各スキャンステップは教材向けに `continueOnError: true` としており、脆弱性を検出してもパイプラインは継続します。実運用ではビルドゲート（しきい値での失敗）を設定してください。
- 拡張機能・ツールのバージョンは将来変更される可能性があります。

## ライセンス

[MIT License](LICENSE)
