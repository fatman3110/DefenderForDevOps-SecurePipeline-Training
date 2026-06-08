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
   - パイプライン変数を変更する。

     ```yaml
     - name: USE_DEFENDER_FOR_DEVOPS
       value: 'true'
     ```

   - パイプラインを再実行すると `MicrosoftSecurityDevOps@1` タスクが動作し、結果が `CodeAnalysisLogs`（`msdo.sarif`）として発行される。

5. **結果の確認**
   - Defender for Cloud > **DevOps security** ブレードで、リポジトリ単位の検出結果を確認する。
   - データが反映されるまで時間がかかる場合がある。

## OSS ツールとの重複について

本パイプラインでは OSS の Bandit / Trivy などを個別ステージで常時実行している。Microsoft Security DevOps も同種のツール（例: Trivy）を内包するため、結果が重複しないよう本教材の Microsoft Security DevOps ステージでは `tools: 'trivy'` のみに限定している。Microsoft Security DevOps 側で実行するツールは要件に合わせて調整すること。

## CodeQL（GitHub Advanced Security for Azure DevOps）との違い

- **CodeQL** は GitHub Advanced Security for Azure DevOps の機能で、結果は **Advanced Security > Code scanning alerts** に表示される。Microsoft Defender for Cloud の DevOps security とは別系統で、別途 GitHub Advanced Security for Azure DevOps のライセンスが必要になる。
- **Microsoft Security DevOps**（本ページの連携）は Microsoft Defender for Cloud 側に集約する仕組みで、Microsoft Defender Cloud Security Posture Management が前提となる。
