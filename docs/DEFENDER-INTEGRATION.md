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
| リポジトリ種別 | **Azure Repos Git（TfsGit）** のみ対応 |
| リージョン | Defender for Cloud の DevOps コネクタが提供されるリージョンに限定される |
| 拡張機能 | [Microsoft Security DevOps](https://marketplace.visualstudio.com/items?itemName=ms-securitydevops.microsoft-security-devops-azdevops) 拡張のインストール |

## 連携手順

1. **Microsoft Defender Cloud Security Posture Management の有効化**
   - Azure portal で **Microsoft Defender for Cloud** > **Environment settings** を開く。
   - 対象サブスクリプションで **Defender CSPM**（Microsoft Defender Cloud Security Posture Management）プランを On にする。

2. **Azure DevOps 拡張のインストール**
   - Azure DevOps 組織に [Microsoft Security DevOps](https://marketplace.visualstudio.com/items?itemName=ms-securitydevops.microsoft-security-devops-azdevops) 拡張をインストールする（要 Project Collection Administrator）。

3. **DevOps コネクタの作成**
   - Defender for Cloud > **Environment settings** > **Add environment** > **Azure DevOps** を選択する。
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

公式ドキュメントに記載されている、Microsoft Security DevOps が内包する主なツールは次のとおり（最終更新の状況は出典を参照）。

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

本教材では重複を避けるため、ツールを次のように役割分担している。本体パイプラインの OSS ステージでは **Bandit（SAST）** を常時実行し、**コンテナー／IaC スキャンは Microsoft Security DevOps を有効化したときに同ステージ側で実行**する。Microsoft Security DevOps ステージでは `tools: 'trivy,checkov'` に限定し（**Trivy** = コンテナイメージ、**Checkov** = IaC / Dockerfile）、本体 OSS ステージの Bandit と重複しないようにしている。

> `USE_DEFENDER_FOR_DEVOPS` を有効化していない既定状態では、本体パイプラインに Trivy / Checkov のステージは含まれず、コンテナー／IaC スキャンは実行されない。Microsoft Security DevOps 側で実行するツールは要件に合わせて調整すること。

## CodeQL（GitHub Advanced Security for Azure DevOps）との違い

- **CodeQL** は GitHub Advanced Security for Azure DevOps の機能で、結果は **Azure DevOps ポータル**（`dev.azure.com`）のリポジトリ画面 **Advanced Security > Code scanning alerts** に表示される（GitHub.com の画面ではない）。Microsoft Defender for Cloud の DevOps security とは別系統で、別途 GitHub Advanced Security for Azure DevOps のライセンスが必要になる。
- 本ページの連携は **Microsoft Defender for Cloud** 側に集約する仕組みで、Microsoft Defender Cloud Security Posture Management が前提となる。
