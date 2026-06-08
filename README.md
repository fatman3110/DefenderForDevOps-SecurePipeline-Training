# DefenderForDevOps SecurePipeline Training

Azure DevOps Pipelines を使った DevSecOps（セキュア CI/CD）の基本を学ぶための教材である。意図的に脆弱性を埋め込んだ Flask Web アプリケーションを題材に、ビルド・単体テスト・各種セキュリティスキャン・コンテナビルド・デプロイを通すパイプラインを構築し、実際にスキャン結果を確認したうえで脆弱性を修正する一連の流れを体験する。

OSS スキャナ（Bandit / Semgrep / Gitleaks / pip-audit / OWASP ZAP）は追加ライセンスなしで常時実行する。コンテナー／IaC スキャン（Trivy / Checkov）は重複を避けるため本体では実行せず、Microsoft Security DevOps を有効化したときに同ステージ側で実行する。CodeQL（GitHub Advanced Security for Azure DevOps の機能）と Microsoft Security DevOps（Microsoft Defender for Cloud 連携）は有償ライセンスが前提のため、フラグで任意に有効化する。

> ⚠️ **教育目的の教材である。アプリケーションは意図的に脆弱性を含む。本番環境では使用しないこと。**

## 前提条件

| 項目 | 内容 | ライセンス |
|------|------|-----------|
| Azure DevOps 組織 / プロジェクト | パイプライン実行環境 | 無料枠で可 |
| Microsoft-hosted agent (`ubuntu-latest`) | パイプラインを実行するマシン（Microsoft 提供の使い捨て VM）使い捨ての Ubuntu マシン（agent）の上で、アプリのコンテナイメージをビルドして Azure に送る。 | 無料枠 / 並列ジョブ |
| [SARIF SAST Scans Tab](https://marketplace.visualstudio.com/items?itemName=sariftools.scans) 拡張 | Azure DevOps **組織**に一度だけインストールする拡張機能。各スキャナが出力する SARIF ファイル（脆弱性の検出結果フォーマット）を、パイプライン実行結果の **Scans** タブで一覧表示できるようにする。未インストールでもパイプラインは動くが、結果を GUI で確認できない | 無料 |
| CodeQL（任意） | GitHub Advanced Security for Azure DevOps の機能 | 有償（GitHub Advanced Security）|
| Microsoft Security DevOps（任意） | Microsoft Defender for Cloud との連携 | 有償（Microsoft Defender Cloud Security Posture Management） |

### 操作に必要な権限とロール

各作業に必要なロールと、そのロールが属するレイヤ（管理基盤）は以下のとおりである。Azure DevOps のロール（セキュリティグループ）と、Azure RBAC ・ Microsoft Entra ID のロールは別のレイヤである。

| 作業 | 区分 | 必要なロール | 補足 |
|------|------|------------|------|
| パイプラインの作成・実行 | **必須** | Azure DevOps ロール（プロジェクトレベル）: **Contributors** | 通常のプロジェクトメンバーで可 |
| SARIF SAST Scans Tab 拡張のインストール | 任意（推奨） | Azure DevOps ロール（組織レベル）: **Project Collection Administrators**（または組織 Owner） | スキャン結果を **Scans** タブで確認するために使用。権限がない一般ユーザーは拡張を「リクエスト」し、上記管理者が承認・インストールする |
| CodeQL（GitHub Advanced Security for Azure DevOps）の有効化 | 任意 | Azure DevOps ロール（プロジェクトレベル）: **Project Administrators** | 有償ライセンスが前提。課金の有効化には組織 Owner が必要 |
| Microsoft Security DevOps（Microsoft Defender for Cloud 連携） | 任意 | Azure RBAC（サブスクリプション）: **Owner** または **Security Admin**<br>Azure DevOps ロール（組織レベル）: **Project Collection Administrators** | 有償ライセンスが前提。連携手順は [`docs/DEFENDER-INTEGRATION.md`](./docs/DEFENDER-INTEGRATION.md) |
| Azure へのデプロイ（Azure Container Registry / Azure App Service）の準備 | 任意 | Azure RBAC（サブスクリプション／リソースグループ）: リソース作成に **Owner** / **Contributor**、RBAC 付与に **User Access Administrator** または **Owner**<br>Azure DevOps ロール（プロジェクトレベル）: **Endpoint Administrator**（または **Project Administrators**） | デプロイして動作確認する場合のみ必要。手順は [`docs/AZURE-SETUP.md`](./docs/AZURE-SETUP.md) |

> ロールの名称と付与手順は変更される可能性がある。最新情報は公式ドキュメントを参照すること。

## 構成ファイル

```text
DefenderForDevOps-SecurePipeline-Training/
├── azure-pipelines.yml              # CI/CD パイプライン定義（ビルド・テスト・スキャン・デプロイ）
├── app/                             # 脆弱性を含む Flask アプリケーション
│   ├── app.py                       # アプリケーション本体
│   ├── templates/                   # 画面テンプレート（index / login / profile）
│   ├── requirements.txt             # 依存ライブラリ（意図的に旧バージョン）
│   └── Dockerfile                   # コンテナイメージ定義
├── tests/
│   └── test_app.py                  # 機能ユニットテスト（修正後の回帰確認用）
├── tools/
│   └── pipaudit_to_sarif.py         # pip-audit JSON → SARIF 変換ツール
└── docs/
    ├── LAB-GUIDE.md                 # 演習ガイド（結果確認場所・脆弱性発見手順）
    ├── AZURE-SETUP.md               # 事前準備ガイド（第1部: Azure DevOps 作成 / 第2部: Azure デプロイ準備）
    ├── SOLUTION.md                  # 脆弱性の修正方法（解答）
    └── DEFENDER-INTEGRATION.md      # Defender for Cloud 連携手順
```

## パイプラインのデータフロー

```text
Build ─▶ Test ─┬─▶ SAST (Bandit + Semgrep) ─┐
               ├─▶ SCA (pip-audit)          ├─▶ DockerBuild ─▶ PublishScans ─▶ Deploy
               ├─▶ Secret (Gitleaks)        ┘
               │
               ├─▶ DAST (OWASP ZAP)            （独立: Artifacts に HTML レポート）
               ├─▶ CodeQL                      （任意: USE_CODEQL=true / GitHub Advanced Security for Azure DevOps）
               └─▶ Microsoft Security DevOps   （任意: USE_DEFENDER_FOR_DEVOPS=true / Trivy + Checkov）
```

## トレーニング手順

1. 本フォルダの内容を Azure DevOps の Git リポジトリにプッシュする。Azure DevOps の組織・プロジェクトがまだない場合は、先に [第1部（共通の事前準備）](./docs/AZURE-SETUP.md#第1部-共通の事前準備必須) で作成する。
2. Azure DevOps 組織に [SARIF SAST Scans Tab](https://marketplace.visualstudio.com/items?itemName=sariftools.scans) 拡張をインストールする。この作業は Azure DevOps 組織の **Project Collection Administrators** グループのメンバーが行う（詳細は上記「必要な権限とロール」を参照）。
3. **Pipelines** > **New pipeline** > **Azure Repos Git** を選択し、リポジトリの [`azure-pipelines.yml`](./azure-pipelines.yml) を指定する。
4. パイプラインを実行する。次のいずれかの方法で実行できる。

   **4-1. 任意のタイミングで手動実行する（コード変更なし）**

   1. **Pipelines** から対象のパイプラインを開く。
   2. 右上の **Run pipeline**（パイプラインの実行）をクリックする。
   3. 実行するブランチ（例: `master`）を選び、**Run** をクリックする。
   4. すぐにパイプラインが起動し、ビルド・テスト・各スキャンが実行される。

   > 手順 3 で初めてパイプラインを作成した直後は、自動的に 1 回目の実行が開始される。

   **4-2. 新しくコードをコミットして実行する（CI トリガー）**

   `azure-pipelines.yml` の `trigger` に指定されたブランチ（`main` / `master`）へコミットを push すると、パイプラインが自動で起動する。脆弱性を修正してから再実行し、スキャン結果が改善することを確認する流れに使う。

   ```bash
   git add .
   git commit -m "fix: 脆弱性を修正"
   git push origin master
   ```

   > `*.md` や `docs/` 配下だけの変更は `trigger` の `paths` 除外により起動しない（ドキュメント編集ではパイプラインが回らない）。
5. 実行完了後、各結果を確認する（詳細は [`docs/LAB-GUIDE.md`](./docs/LAB-GUIDE.md)）。
   - **Scans** タブ: SAST / SCA / Secret / Container の SARIF 結果
   - **Tests** タブ: pytest の結果
   - **Artifacts**（`zap-report`）: OWASP ZAP の DAST レポート（HTML）

> パイプライン作成・拡張インストールの最新手順は、変更される可能性がある。最新手順は公式ドキュメントを参照すること。
> - [Create your first pipeline](https://learn.microsoft.com/azure/devops/pipelines/create-first-pipeline)
> - [Install extensions](https://learn.microsoft.com/azure/devops/marketplace/install-extension)

## (オプション) デプロイしたアプリケーションへのアクセス

パイプラインの `Deploy` ステージは、ビルドしたコンテナイメージを **Azure Container Registry** にプッシュし、**Azure App Service**（PaaS ランタイム実行環境） にデプロイする。デプロイ後は Azure App Service の URL `https://<webAppName>.azurewebsites.net` でアプリにアクセスでき、脆弱性の手動確認（XSS・アクセスコントロール・Cookie など）が当該 URL 上で行える。
本手順を行わない場合でも、CI/CD パイプラインの実行と脆弱性の確認が可能である。

> **Azure Container Registry や Azure App Service などの Azure リソースはパイプラインでは自動作成されない。** リソースの作成、サービス接続・RBAC の設定、そして作成した値をパイプライン変数のどこに反映するかの詳細な GUI 操作手順は **[`docs/AZURE-SETUP.md`](./docs/AZURE-SETUP.md)** を参照すること。

### 環境準備概要（詳細は事前準備ガイド）

1. [`docs/AZURE-SETUP.md`](./docs/AZURE-SETUP.md) に従って Azure リソースを作成する。
2. リソース作成時に控えた値を [`azure-pipelines.yml`](./azure-pipelines.yml) の `variables` に反映したうえで、環境へのデプロイを有効化する。

   | 控えた値 | パイプライン変数 | 例 |
   |-----------|----------------|----|
   | Azure Container Registry のログインサーバー | `acrLoginServer` | `acrdevsecopstraining.azurecr.io` |
   | Azure App Service（Web アプリ）の名前 | `webAppName` | `app-devsecops-training` |
   | サービス接続の名前 | `azureServiceConnection` | `sc-devsecops-training` |
   | デプロイ有効化 | `DEPLOY_TO_AZURE` | `true` |

3. パイプラインを実行する。`Deploy` ステージが Azure Container Registry へのプッシュと Azure App Service へのデプロイを行う。
4. デプロイ後、`https://<webAppName>.azurewebsites.net` にアクセスする。

> `DEPLOY_TO_AZURE` が `true` でない場合、`Deploy` ステージはデプロイを行わずスキップ用のメッセージを表示して終了する（ビルドとスキャンは引き続き実行される）。

### デプロイ後の Web アプリケーション画面一覧

| URL | 内容 |
|-----|------|
| `https://<webAppName>.azurewebsites.net/` | トップページ |
| `https://<webAppName>.azurewebsites.net/login` | ログイン（`alice` / `alice-password`、`bob` / `bob-password`） |
| `https://<webAppName>.azurewebsites.net/profile/1` | プロフィール（アクセスコントロールの脆弱性の確認に使用） |
| `https://<webAppName>.azurewebsites.net/search?q=test` | 検索（クロスサイトスクリプティングの確認に使用） |

###  (オプション) ローカルでの起動

Azure 環境を使わずに手元で動作確認する場合は、Docker が動作する PC でリポジトリのルートから次を実行する。

```bash
docker build -t training-app ./app
docker run -d --name training-app -p 5000:5000 training-app
# 確認後: docker rm -f training-app
```

ブラウザで `http://localhost:5000` を開く。

## 技術仕様

### 任意フラグ

| 変数 | 既定値 | 説明 |
|------|--------|------|
| `USE_CODEQL` | `false` | `true` で CodeQL ステージを実行（GitHub Advanced Security for Azure DevOps のライセンス必須） |
| `USE_DEFENDER_FOR_DEVOPS` | `false` | `true` で Microsoft Security DevOps ステージを実行（Microsoft Defender Cloud Security Posture Management 必須） |

#### 任意フラグの変更方法

[`azure-pipelines.yml`](./azure-pipelines.yml) の `variables` ブロックを書き換えてコミットする。

```yaml
variables:
  - name: USE_CODEQL
    value: 'true'              # false -> true に変更
  - name: USE_DEFENDER_FOR_DEVOPS
    value: 'true'              # false -> true に変更
```

対応する拡張・ライセンスが未導入の場合は該当ステージはプレースホルダのまま終了する（詳細は  [`docs/DEFENDER-INTEGRATION.md`](./docs/DEFENDER-INTEGRATION.md) を参照）。

### スキャン結果の確認場所

| ツール | 種別 | 確認場所 |
|--------|------|---------|
| Bandit | SAST | Scans タブ |
| Semgrep | SAST | Scans タブ |
| pip-audit | SCA | Scans タブ |
| Gitleaks | Secret | Scans タブ |
| Trivy / Checkov | Container / IaC | Microsoft Security DevOps 有効時のみ（Scans タブ / DevOps security） |
| OWASP ZAP | DAST | Artifacts（`zap-report` の HTML レポート） |
| CodeQL | SAST | Advanced Security > Code scanning alerts |
| Microsoft Security DevOps | 集約 | Microsoft Defender for Cloud > DevOps security |

## 確認対象の脆弱性

| # | 脆弱性 | 該当箇所 |
|---|--------|---------|
| 1 | ハードコードされた認証情報（ダミー） | [`app/app.py`](./app/app.py) の `SECRET_KEY` / `DB_PASSWORD` / AWS キー |
| 2 | HttpOnly のない Cookie | `/login` の `set_cookie(httponly=False)` |
| 3 | 古い脆弱なライブラリ | [`app/requirements.txt`](./app/requirements.txt)（Flask 2.0.1 等） |
| 4 | クロスサイトスクリプティング（XSS） | `/search` の `render_template_string` |
| 5 | アクセスコントロールの脆弱性（IDOR） | `/profile/<user_id>` の認可チェック欠落 |

修正方法は [`docs/SOLUTION.md`](./docs/SOLUTION.md) を参照すること。

## 注意事項

- 本教材は公式 Microsoft 製品ではなく、DevSecOps を学習するためのサンプルである。
- アプリケーションは意図的に脆弱性を含む。**隔離された検証環境またはローカルでのみ実行すること。**
- 各スキャンステップは教材向けに `continueOnError: true` としており、脆弱性を検出してもパイプラインは継続する。実運用では閾値に応じたエラーハンドリングを設定すること。
- 拡張機能・ツールのバージョンは将来変更される可能性がある。

## ライセンス

[MIT License](LICENSE)
