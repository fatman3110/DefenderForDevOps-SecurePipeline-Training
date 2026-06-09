# Microsoft Defender for Cloud 連携（DEFENDER INTEGRATION）

本教材の任意ステージ Microsoft Security DevOps を有効化し、スキャン結果を Microsoft Defender for Cloud の **DevOps security** に集約表示する手順を示す。この連携は有償の Microsoft Defender Cloud Security Posture Management プランが前提となる。

> 連携手順は変更される可能性がある。最新手順は公式ドキュメントを参照すること。
> - [Azure DevOps 環境を Defender for Cloud に接続する](https://learn.microsoft.com/azure/defender-for-cloud/quickstart-onboard-devops)
> - [Microsoft Security DevOps Azure DevOps 拡張を構成する](https://learn.microsoft.com/azure/defender-for-cloud/azure-devops-extension)

## 前提条件

| 項目 | 内容 |
|------|------|
| Defender for Cloud | **Microsoft Defender Cloud Security Posture Management** プランの有効化が必要 |
| 権限 | Azure サブスクリプションの **Subscription Contributor**（または Owner） |
| Azure DevOps 権限 | コネクタ作成時に **Project Collection Administrator** |
| リポジトリ種別 | **Azure Repos の Git リポジトリ**のみ対応 |
| リージョン | Defender for Cloud の DevOps セキュリティが提供されるリージョンに限定される（例: East Asia / Australia East / Canada Central / West Europe / North Europe / Sweden Central / UK South / East US / Central US）。最新の対応リージョンは [DevOps セキュリティのサポートと前提条件](https://learn.microsoft.com/azure/defender-for-cloud/devops-support#cloud-and-region-support) を参照 |
| 拡張機能 | [Microsoft Security DevOps](https://marketplace.visualstudio.com/items?itemName=ms-securitydevops.microsoft-security-devops-azdevops) 拡張のインストール |

## 連携手順

1. **Microsoft Defender Cloud Security Posture Management の有効化**
   - [Azure Portal](https://portal.azure.com) を開き、 **Microsoft Defender for Cloud** > **環境設定** を開く。
   - 対象サブスクリプションで **Defender CSPM**（Microsoft Defender Cloud Security Posture Management）プランを On にする。

2. **Azure DevOps 拡張のインストール**

   拡張のインストールには **Project Collection Administrator**（組織の管理者グループ。組織の Owner は自動的にこのメンバー）の権限が必要。権限がない場合は手順 2-2 で「リクエスト」して管理者に承認してもらう。

   **2-1. 自分の権限を確認する**
   1. ブラウザで Azure DevOps 組織（`https://dev.azure.com/{組織名}`）にサインインする。
   2. 左下の歯車アイコン **[Organization settings]**（組織の設定）を開く。
   3. **[Security]** > **[Permissions]** を開き、グループ一覧から **[Project Collection Administrators]** を選択する。
   4. **[Members]** タブに自分のアカウントが含まれていれば、インストール権限がある（手順 2-2 でそのままインストールできる）。含まれていなければ、管理者にメンバー追加を依頼するか、手順 2-2 で拡張を「リクエスト」する。
      - 組織の Owner は **[Organization settings]** > **[Overview]** の **Owner** 欄で確認できる。

   **2-2. 拡張をインストールする（または承認をリクエストする）**
   5. Azure DevOps の上部ツールバーの **ショッピングバッグ アイコン** > **[Manage extensions]** を開く。
   6. **[Browse marketplace]** を選択する。
   7. 検索ボックスに「Microsoft Security DevOps」と入力し、[Microsoft Security DevOps](https://marketplace.visualstudio.com/items?itemName=ms-securitydevops.microsoft-security-devops-azdevops) 拡張を開く。
   8. **[Get it free]**（無料で入手）を選択し、ドロップダウンで対象の **組織** を選んで **[Install]** を選択する。
      - **権限がある場合**: インストールが完了し、**[Proceed to organization]** で組織に戻る。
      - **権限がない場合**: ボタンが **[Request]**（リクエスト）になる。リクエストすると Project Collection Administrator にメール通知が届き、承認されると自動的にインストールされる。リクエストの状況は **[Organization settings]** > **[Extensions]** > **[Requested]** タブで確認できる。
   9. インストール後、**[Organization settings]** > **[Extensions]** > **[Installed]** タブに **Microsoft Security DevOps** が表示されることを確認する。

   > 参考: [拡張機能のインストール](https://learn.microsoft.com/azure/devops/marketplace/install-extension) / [拡張機能のリクエストと承認](https://learn.microsoft.com/azure/devops/marketplace/request-extensions) / [Project Collection Administrators の確認](https://learn.microsoft.com/azure/devops/organizations/security/look-up-project-collection-administrators)

3. **DevOps コネクタの作成**
   - [Azure Portal](https://portal.azure.com) を開き、 **Microsoft Defender for Cloud** >  **環境設定** > **環境を追加** > **Azure DevOps** を選択する。
   - 画面の指示に従って Azure DevOps 組織を認可し、対象プロジェクト／リポジトリを選択する。

4. **パイプラインで Microsoft Security DevOps を有効化**
   - リポジトリ直下の [`azure-pipelines.yml`](../azure-pipelines.yml) を開き、`variables:` ブロック内にある `USE_DEFENDER_FOR_DEVOPS` の `value` を `'false'` から `'true'` に書き換える。

     ```yaml
     variables:
       # ... 既存の変数 ...
       - name: USE_DEFENDER_FOR_DEVOPS
         value: 'true'              # 'false' から変更
     ```

   - 変更を保存し、`trigger` 対象ブランチ（`main` / `master`）へコミットして push する。

     ```bash
     git add azure-pipelines.yml
     git commit -m "enable Microsoft Security DevOps stage"
     git push origin master
     ```

   - push により CI トリガーでパイプラインが再実行される（または Azure DevOps の **Run pipeline** から手動実行する）。`USE_DEFENDER_FOR_DEVOPS` が `true` のとき `MicrosoftSecurityDevOps@1` タスクが動作し、結果が `CodeAnalysisLogs`（`msdo.sarif`）として発行される。

5. **結果の確認**
   - Defender for Cloud > **DevOps security** ブレードで、リポジトリ単位の検出結果を確認する。
   - データが反映されるまで時間がかかる場合がある。

## OSS ツールとの重複について

Microsoft Security DevOps は、複数の静的解析ツールを内包したコマンドラインアプリケーションである。`MicrosoftSecurityDevOps@1` タスクの `tools` 入力で実行するツールを限定できる（既定はポリシーに従い全ツール）。

公式ドキュメントに記載されている、Microsoft Security DevOps が内包する主なツールは次のとおり。

| ツール | 主な対象 | カテゴリ |
|--------|---------|---------|
| AntiMalware | Windows 上のマルウェアスキャン（Windows-latest エージェントで既定実行） | malware |
| Bandit | Python ソースコード | code |
| BinSkim | バイナリ（Windows / ELF） | artifacts |
| Checkov | Terraform / CloudFormation / Kubernetes / Helm / Dockerfile / Bicep / ARM ほか | IaC |
| ESLint | JavaScript | code |
| IaCFileScanner | Terraform / CloudFormation / ARM / Bicep のテンプレートマッピング | IaC |
| Template Analyzer | ARM テンプレート / Bicep（PSRule を含む） | IaC |
| Terrascan | Terraform / Kubernetes / Helm / Kustomize / Dockerfile / CloudFormation | IaC |
| Trivy | コンテナイメージ / IaC | containers / IaC |

> `tools` 入力で指定できる値は `bandit` / `binskim` / `checkov` / `eslint` / `templateanalyzer` / `terrascan` / `trivy`。`categories` 入力（`code` / `artifacts` / `IaC` / `containers`）でカテゴリ単位の絞り込みも可能。
>
> **シークレットスキャン（CredScan）は 2023年9月20日に非推奨化**され、その役割は **GitHub Advanced Security for Azure DevOps** に置き換えられている。本教材ではシークレット検出に OSS の Gitleaks を使用している。
> 出典: [Configure the Microsoft Security DevOps Azure DevOps extension](https://learn.microsoft.com/azure/defender-for-cloud/configure-azure-devops-extension)（ツール一覧・`tools`/`categories` 入力・CredScan 非推奨の記載）

本教材では重複を避けるため、ツールを次のように役割分担している。本体パイプラインの OSS ステージでは **Bandit（SAST）** を常時実行し、**コンテナー／IaC スキャンは Microsoft Security DevOps を有効化したときに同ステージ側で実行**する。


## CodeQL（GitHub Advanced Security for Azure DevOps）との違い

- **CodeQL** は GitHub Advanced Security for Azure DevOps の機能で、結果は **Azure DevOps ポータル**（`dev.azure.com`）のリポジトリ画面 **Advanced Security > Code scanning alerts** に表示される。Microsoft Defender for Cloud の DevOps security とは別系統で、別途 GitHub Advanced Security for Azure DevOps のライセンスが必要になる。
