# 演習ガイド（LAB GUIDE）

本ガイドでは、パイプラインを実行したあとにスキャン結果をどこで確認し、各脆弱性をどのように見つけるかを説明する。修正方法は [`SOLUTION.md`](./SOLUTION.md) を参照すること。

## 1. パイプラインの実行

1. リポジトリを Azure DevOps にプッシュする。
2. **Pipelines** からパイプラインを実行する。
3. 全ステージが完了するまで待つ（本トレーニングでは、セキュリティスキャンが `continueOnError: true` に設定されているため、脆弱性を検出してもすべてのパイプラインが完了するが、本番環境ではリスクに沿った実装が必要な点に留意）。

## 2. 結果の確認場所

| 確認したいもの | 確認場所 | 補足 |
|----------------|---------|------|
| 単体テスト結果 | パイプライン実行 > **Tests** タブ | pytest の合否 |
| SAST / SCA / Secret / Container | パイプライン実行 > **Scans** タブ | SARIF SAST Scans Tab 拡張が必要 |
| DAST（ZAP） | パイプライン実行 > **Artifacts** > `zap-report` | `zap-report.html` をダウンロード |
| 各ツールの生ログ | 各ステージのジョブログ | コマンド出力をそのまま確認 |
| CodeQL（任意） | **Advanced Security** > **Code scanning alerts** | `USE_CODEQL=true` かつ GitHub Advanced Security for Azure DevOps |
| Microsoft Security DevOps（任意） | Defender for Cloud > **DevOps security** | `USE_DEFENDER_FOR_DEVOPS=true` |

> **Scans** タブが表示されない場合は、[SARIF SAST Scans Tab](https://marketplace.visualstudio.com/items?itemName=sariftools.scans) 拡張がインストールされているか確認する。SARIF は `CodeAnalysisLogs` アーティファクトに集約される。

## 3. 脆弱性の発見手順

> **想定検出ルール** は、各ツールがこの脆弱性を検出することを意図したルール・カテゴリを示す。スキャナのバージョンやルールセット、コードの書き方によっては検出されない場合もあるため、自動検出に加えて手動確認も行うこと。

### #1 ハードコードされた認証情報

- **脆弱性概要**: ソースコードやリポジトリに API キー・パスワード・接続文字列などのシークレットを直書きすると、リポジトリの閲覧権限を持つ全員に漏えいする。Git 履歴・フォーク・バックアップを通じて拡散し、いったん漏れたクレデンシャルの無効化は難しい。漏えいした資格情報は不正アクセス・データ窃取・課金リソースの悪用につながる。今回のケースでは [`app/app.py`](../../app/app.py) の冒頭に `SECRET_KEY` / `DB_PASSWORD` / AWS アクセスキーが直書きされており、リポジトリを読めれば誰でも取得できる状態になっている。
- **想定検出ルール**: Gitleaks（Secret）、Bandit（SAST）
- **自動脆弱性テスト結果の確認**: Scans タブで `SECRET_KEY` / `DB_PASSWORD` / AWS キーの検出を確認する。
- **手動での脆弱性確認**: [`app/app.py`](../../app/app.py) の上部にシークレットが直書きされている。

### #2 HttpOnly のない Cookie

- **脆弱性概要**: セッション Cookie に `HttpOnly` 属性がないと JavaScript（`document.cookie`）から読み取れてしまい、XSS と組み合わせるとセッショントークンを盗まれてセッションハイジャックにつながる。`Secure` 属性がなければ平文 HTTP でも送信され盗聴の対象になる。今回のケースでは `/login` が `user_session` Cookie を `httponly=False` / `secure=False` で発行しており、後述の XSS（#4）と組み合わせるとセッションを奪取できる。
- **想定検出ルール**: Bandit（SAST）、OWASP ZAP（DAST）
- **自動脆弱性テスト結果の確認**: ZAP レポート（`zap-report.html`）の "Cookie No HttpOnly Flag" アラートを確認する。
- **手動での脆弱性確認**: アプリにログイン後、ブラウザの開発者ツールのコンソールで `document.cookie` を実行すると `user_session` が読み取れる。

### #3 古い脆弱なライブラリ

- **脆弱性概要**: 既知の脆弱性（CVE）を含む古い依存ライブラリを使い続けると、公開済みのエクスプロイトで攻撃され得る。アプリ本体のコードが正しくても、依存パッケージ経由で侵害される（サプライチェーン攻撃）リスクがある。今回のケースでは [`app/requirements.txt`](../../app/requirements.txt) が Flask 2.0.1 など旧バージョンに固定されており、既知 CVE を持つ依存を含んでいる。
- **想定検出ルール**: pip-audit（SCA）、Trivy（Container, Microsoft Security DevOps 有効時）
- **自動脆弱性テスト結果の確認**: Scans タブで Flask 2.0.1 などの依存ライブラリに紐づく CVE を確認する。
- **手動での脆弱性確認**: [`app/requirements.txt`](../../app/requirements.txt) に旧バージョンが固定されている。

### #4 クロスサイトスクリプティング（XSS）

- **脆弱性概要**: ユーザー入力を検証・エスケープせずに HTML へ出力すると、攻撃者が注入したスクリプトが被害者のブラウザで実行される。これにより Cookie 窃取・画面改ざん・フィッシング・なりすましなどが可能になる。今回のケースでは `/search` が `render_template_string` でクエリ文字列を直接 HTML に連結しており、`q` パラメータに `<script>` を渡すとそのまま実行される（反射型 XSS）。
- **想定検出ルール**: Semgrep / Bandit（SAST）、OWASP ZAP（DAST）
- **自動脆弱性テスト結果の確認**: ZAP レポートの "Cross Site Scripting (Reflected)" を確認する。
- **手動での脆弱性確認**: デプロイ済み Azure App Service の次の URL（ローカル起動時は `http://localhost:5000`）を開くとスクリプトが実行される。

  ```text
  https://<webAppName>.azurewebsites.net/search?q=<script>alert(document.cookie)</script>
  ```

### #5 アクセスコントロールの脆弱性（IDOR）

- **脆弱性概要**: リクエストされたオブジェクト ID に対して認可チェックを行わないと、ID を書き換えるだけで他ユーザーのリソースを閲覧・操作できてしまう（IDOR: Insecure Direct Object Reference）。OWASP Top 10 の Broken Access Control に該当し、ツールによる自動検出が難しい代表例である。今回のケースでは `/profile/<user_id>` がログイン中のユーザーと `user_id` の一致を検証しておらず、URL の ID を変えるだけで他人のプロフィール（SSN・給与）が閲覧できてしまう。
- **想定検出ルール**: 自動検出は困難（手動／ロジック検査が中心）
- **手動での脆弱性確認**（デプロイ済み Azure App Service またはローカル起動の URL で実施）:
  1. `alice` / `alice-password` でログインする（`/profile/1` が表示される）。
  2. URL を `/profile/2` に書き換える。
  3. ログインユーザーが alice のまま、bob の機密情報（SSN・給与）が閲覧できてしまう。

## 4. 修正と回帰確認

1. [`SOLUTION.md`](./SOLUTION.md) を参考に各脆弱性を修正する。
2. ローカルで単体テストを実行し、機能が壊れていないことを確認する。

   ```bash
   pip install -r app/requirements.txt pytest
   python -m pytest tests/ -v
   ```

3. 再度パイプラインを実行し、Scans タブ・ZAP レポートで指摘が解消されたことを確認する。
