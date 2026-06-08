# 演習ガイド（LAB GUIDE）

本ガイドでは、パイプラインを実行したあとにスキャン結果をどこで確認し、各脆弱性をどのように見つけるかを説明する。修正方法は [`SOLUTION.md`](./SOLUTION.md) を参照すること。

## 1. パイプラインの実行

1. リポジトリを Azure DevOps にプッシュする。
2. **Pipelines** からパイプラインを実行する。
3. 全ステージが完了するまで待つ（セキュリティスキャンは `continueOnError: true` のため、脆弱性を検出しても緑のまま完了する）。

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

### #1 ハードコードされた認証情報

- **検出ツール**: Gitleaks（Secret）、Bandit（SAST）
- **確認**: Scans タブで `SECRET_KEY` / `DB_PASSWORD` / AWS キーの検出を確認する。
- **手動確認**: [`app/app.py`](../app/app.py) の上部にシークレットが直書きされている。

### #2 HttpOnly のない Cookie

- **検出ツール**: Bandit（SAST）、OWASP ZAP（DAST）
- **確認**: ZAP レポート（`zap-report.html`）の "Cookie No HttpOnly Flag" アラートを確認する。
- **手動確認**: アプリにログイン後、ブラウザの開発者ツールのコンソールで `document.cookie` を実行すると `user_session` が読み取れる。

### #3 古い脆弱なライブラリ

- **検出ツール**: pip-audit（SCA）、Trivy（Container）
- **確認**: Scans タブで Flask 2.0.1 などの依存ライブラリに紐づく CVE を確認する。
- **手動確認**: [`app/requirements.txt`](../app/requirements.txt) に旧バージョンが固定されている。

### #4 クロスサイトスクリプティング（XSS）

- **検出ツール**: Semgrep / Bandit（SAST）、OWASP ZAP（DAST）
- **確認**: ZAP レポートの "Cross Site Scripting (Reflected)" を確認する。
- **手動確認**: デプロイ済み Azure App Service の次の URL（ローカル起動時は `http://localhost:5000`）を開くとスクリプトが実行される。

  ```text
  https://<webAppName>.azurewebsites.net/search?q=<script>alert(document.cookie)</script>
  ```

### #5 アクセスコントロールの脆弱性（IDOR）

- **検出ツール**: 自動検出は困難（手動／ロジック検査が中心）
- **手動確認**（デプロイ済み Azure App Service またはローカル起動の URL で実施）:
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
