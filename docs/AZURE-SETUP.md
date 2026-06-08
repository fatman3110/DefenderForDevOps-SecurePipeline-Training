# Azure デプロイ事前準備ガイド

このパイプラインの `Deploy` ステージは、ビルドしたコンテナイメージを **Azure Container Registry（ACR）** に push し、**Azure Web App for Containers** にデプロイする。これらの Azure リソースとサービス接続は**パイプラインでは自動作成されない**ため、事前に手動で用意する。

本ガイドでは、Azure Portal と Azure DevOps の GUI 操作でリソースを作成し、作成した値を [`azure-pipelines.yml`](../azure-pipelines.yml) のどの変数に反映するかまでを説明する。

> 画面名・メニュー位置・ボタン名は変更される可能性がある。最新の手順は各公式ドキュメントを参照すること。

## 全体像

```text
[Azure Portal]                          [Azure DevOps]
 1. リソースグループ                      4. サービス接続(ARM)
 2. Azure Container Registry  ──────┐     5. パイプライン変数へ反映
 3. Web App for Containers          │
       │                            │
       └── サービスプリンシパルに ───┘
            AcrPush / Contributor を付与
```

## 準備するもの一覧

| # | リソース／設定 | 作成場所 | 反映先（パイプライン変数など） |
|---|----------------|----------|-------------------------------|
| 1 | リソースグループ | Azure Portal | （変数には直接反映しない。下記リソースの入れ物） |
| 2 | Azure Container Registry | Azure Portal | ログインサーバー → `acrLoginServer` |
| 3 | Web App for Containers | Azure Portal | アプリ名 → `webAppName` |
| 4 | Azure Resource Manager サービス接続 | Azure DevOps | 接続名 → `azureServiceConnection` |
| 5 | RBAC ロール割り当て（AcrPush / Contributor） | Azure Portal | （変数なし。サービス接続の権限） |
| 6 | デプロイ有効化フラグ | パイプライン変数 | `DEPLOY_TO_AZURE` を `true` |

---

## 1. リソースグループの作成（Azure Portal）

1. [Azure Portal](https://portal.azure.com) にサインインする。
2. 上部の検索ボックスに「リソース グループ」と入力し、**リソース グループ** を開く。
3. **作成** をクリックする。
4. 次を入力する。
   - **サブスクリプション**: 利用するサブスクリプション
   - **リソース グループ**: 任意の名前（例: `rg-devsecops-training`）
   - **リージョン**: 任意（例: `Japan East`）
5. **確認および作成** > **作成** をクリックする。

> 参考: [リソース グループの管理](https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)

---

## 2. Azure Container Registry の作成（Azure Portal）

1. 検索ボックスに「Container registries」と入力し、**Container registries** を開く。
2. **作成** をクリックする。
3. **基本** タブで次を入力する。
   - **サブスクリプション** / **リソース グループ**: 手順 1 で作成したもの
   - **レジストリ名**: グローバルに一意な名前（例: `acrdevsecopstraining`）。英数字のみ。
   - **場所**: 手順 1 と同じリージョン
   - **SKU**: `Basic`（教材用途では十分）
4. **確認および作成** > **作成** をクリックする。
5. 作成後、レジストリのリソースを開き、**概要** に表示される **ログイン サーバー**（例: `acrdevsecopstraining.azurecr.io`）を控える。

> この **ログイン サーバー** の値を、後でパイプライン変数 `acrLoginServer` に設定する。
> 参考: [コンテナー レジストリの作成](https://learn.microsoft.com/azure/container-registry/container-registry-get-started-portal)

---

## 3. Web App for Containers の作成（Azure Portal）

1. 検索ボックスに「App Services」と入力し、**App Services** を開く。
2. **作成** > **Web アプリ** をクリックする。
3. **基本** タブで次を入力する。
   - **サブスクリプション** / **リソース グループ**: 手順 1 で作成したもの
   - **名前**: グローバルに一意な名前（例: `app-devsecops-training`）。これが URL `https://<名前>.azurewebsites.net` になる。
   - **公開**: **コンテナー**
   - **オペレーティング システム**: **Linux**
   - **地域**: 手順 1 と同じリージョン
   - **Linux プラン / 価格プラン**: 任意（教材用途では `B1` など）
4. **コンテナー** タブで、いったん任意の公開イメージ（例: `nginx`）を指定するか、既定のまま進める。
   - 実際のアプリイメージはパイプラインの `Deploy` ステージが後から設定・デプロイする。
5. **確認および作成** > **作成** をクリックする。
6. 作成後、Web アプリの **概要** に表示される **既定のドメイン**（`https://<名前>.azurewebsites.net`）を控える。

> この Web アプリの **名前** を、後でパイプライン変数 `webAppName` に設定する。
> 参考: [カスタム コンテナーを Azure に対して実行する](https://learn.microsoft.com/azure/app-service/quickstart-custom-container)

---

## 4. Azure Resource Manager サービス接続の作成（Azure DevOps）

パイプラインから Azure を操作するための接続を作成する。

1. Azure DevOps でプロジェクトを開き、左下の **Project settings**（プロジェクト設定）をクリックする。
2. **Pipelines** > **Service connections** を開く。
3. **New service connection** をクリックする。
4. **Azure Resource Manager** を選択して **Next** をクリックする。
5. 認証方法を選ぶ（既定の **Workload Identity federation (automatic)** または **Service principal (automatic)** を推奨）。
6. 次を選択・入力する。
   - **Scope level**: **Subscription**
   - **Subscription**: 対象サブスクリプション
   - **Resource group**: 手順 1 で作成したリソースグループ（任意。絞り込むと安全）
   - **Service connection name**: 任意の名前（例: `sc-devsecops-training`）
   - **Grant access permission to all pipelines**: 教材では有効でよい
7. **Save** をクリックする。

> この **Service connection name** を、後でパイプライン変数 `azureServiceConnection` に設定する。
> 自動作成方式では、対応するサービスプリンシパル（またはマネージド ID）が Microsoft Entra ID に作成される。次の手順 5 でこの ID にロールを付与する。
> 参考: [Azure Resource Manager サービス接続](https://learn.microsoft.com/azure/devops/pipelines/library/connect-to-azure)

---

## 5. RBAC ロールの割り当て（Azure Portal）

手順 4 で作成されたサービスプリンシパル（サービス接続が使う ID）に、ACR への push と Web App へのデプロイの権限を付与する。

### 5-1. サービス接続が使う ID の名前を確認する

1. Azure DevOps の **Project settings** > **Service connections** で、手順 4 のサービス接続を開く。
2. **Manage Service Principal**（または接続詳細）のリンクから、Microsoft Entra ID 上のアプリ（サービスプリンシパル）の名前・アプリケーション ID を控える。

### 5-2. ACR に AcrPush を付与する

1. Azure Portal で手順 2 の Container Registry を開く。
2. 左メニューの **アクセス制御 (IAM)** を開く。
3. **追加** > **ロールの割り当ての追加** をクリックする。
4. **ロール** タブで **AcrPush** を選択する。
5. **メンバー** タブで **+ メンバーを選択する** をクリックし、5-1 で確認したサービスプリンシパルを選ぶ。
6. **レビューと割り当て** をクリックする。

### 5-3. Web App（またはリソースグループ）に Contributor を付与する

1. Azure Portal で手順 3 の Web アプリ、または手順 1 のリソースグループを開く。
2. **アクセス制御 (IAM)** > **追加** > **ロールの割り当ての追加** をクリックする。
3. **ロール** タブで **共同作成者（Contributor）** を選択する。
4. **メンバー** タブで同じサービスプリンシパルを選ぶ。
5. **レビューと割り当て** をクリックする。

> 最小権限を重視する場合は、Contributor の代わりに **Website Contributor** を Web アプリに付与してもよい。
> 参考: [Azure portal を使用して Azure ロールを割り当てる](https://learn.microsoft.com/azure/role-based-access-control/role-assignments-portal)

---

## 6. 準備した値をパイプラインに反映する

手順 2〜4 で控えた値を [`azure-pipelines.yml`](../azure-pipelines.yml) の `variables` ブロックに設定し、`DEPLOY_TO_AZURE` を `true` にする。

```yaml
variables:
  # ... 既存の変数 ...
  - name: DEPLOY_TO_AZURE
    value: 'true'                              # false -> true
  - name: azureServiceConnection
    value: 'sc-devsecops-training'             # 手順 4 のサービス接続名
  - name: acrLoginServer
    value: 'acrdevsecopstraining.azurecr.io'   # 手順 2 のログインサーバー
  - name: webAppName
    value: 'app-devsecops-training'            # 手順 3 の Web アプリ名
```

### 値と変数の対応表

| 控えた値（出どころ） | パイプライン変数 | 例 |
|----------------------|-----------------|----|
| Container Registry のログインサーバー（手順 2-5） | `acrLoginServer` | `acrdevsecopstraining.azurecr.io` |
| Web アプリの名前（手順 3） | `webAppName` | `app-devsecops-training` |
| サービス接続の名前（手順 4） | `azureServiceConnection` | `sc-devsecops-training` |
| デプロイ有効化 | `DEPLOY_TO_AZURE` | `true` |

> 一時的に 1 回だけデプロイしたい場合は、YAML を編集せず、パイプライン実行画面の **Run pipeline** > **Variables** で同名の変数を上書きしてもよい。

---

## 7. デプロイの実行と確認

1. 変数を設定したうえでパイプラインを実行する。
2. `Deploy` ステージが成功すると、ACR へ push され Web App にデプロイされる。
3. ブラウザで `https://<webAppName>.azurewebsites.net` を開き、アプリが表示されることを確認する。

うまくいかない場合は次を確認する。

- `Deploy` ステージがスキップされる → `DEPLOY_TO_AZURE` が `true` か、各変数が空でないか。
- ACR への push が失敗する → サービスプリンシパルに **AcrPush** が付与されているか、`acrLoginServer` が正しいか。
- Web App へのデプロイが失敗する → サービスプリンシパルに **Contributor**（または Website Contributor）が付与されているか、`webAppName` が正しいか。
- ページが表示されない → Web App の **ログ ストリーム** でコンテナ起動ログを確認する。アプリはコンテナ内で 5000 番ポートを使用する。

---

## 後片付け

教材の確認が終わったら、不要な課金を避けるためリソースを削除する。最も簡単なのは手順 1 のリソースグループごと削除する方法である。

1. Azure Portal で手順 1 のリソースグループを開く。
2. 上部の **リソース グループの削除** をクリックし、確認のため名前を入力して削除する。
