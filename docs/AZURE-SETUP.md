# 事前準備ガイド

本ガイドは、本教材を実行するための事前準備を 2 部構成で説明する。

- **[第1部. 共通の事前準備（必須）](#第1部-共通の事前準備必須)**: パイプラインを動かすための土台となる Azure DevOps 組織・プロジェクトを用意する。デプロイの有無にかかわらず必要。
- **[第2部. デプロイ用の事前準備（任意）](#第2部-デプロイ用の事前準備任意)**: ビルドしたアプリを Azure にデプロイして動作確認したい場合のみ必要。Azure Container Registry / Azure App Service / サービス接続を用意する。

> 画面名・メニュー位置・ボタン名は変更される可能性がある。最新の手順は各公式ドキュメントを参照すること。

---

# 第1部. 共通の事前準備（必須）

パイプラインを実行するには、Azure DevOps の**組織**と、その中の**プロジェクト**が必要になる。すでに利用できる組織・プロジェクトがある場合はこの第1部を読み飛ばしてよい。

## A. Azure DevOps 組織の作成

1. ブラウザで [https://dev.azure.com](https://dev.azure.com) を開き、Microsoft アカウントまたは職場・学校アカウントでサインインする。
2. 初めて利用する場合は、画面の案内に従って **New organization**（新しい組織の作成）を進める。
   - 既存の組織がある場合は、左下の **New organization** から追加で作成できる。
3. 組織名（例: `myorg-devsecops`）とホストするリージョンを指定し、作成する。

> 参考: [組織またはプロジェクト コレクションの作成](https://learn.microsoft.com/azure/devops/organizations/accounts/create-organization)

## B. プロジェクトの作成

1. 作成した組織のトップページで **+ New project**（新しいプロジェクト）をクリックする。
2. 次を入力する。
   - **Project name**: 任意の名前（例: `DevSecOps-Training`）
   - **Visibility**: **Private**（教材用途では非公開を推奨）
   - **Version control**: **Git**
3. **Create** をクリックする。

> 参考: [プロジェクトの作成](https://learn.microsoft.com/azure/devops/organizations/projects/create-project)

## C. コードのプッシュ

作成したプロジェクトの **Repos** に本教材一式（このリポジトリの内容）をプッシュする。

> これで第1部は完了。デプロイまで行う場合は [第2部（デプロイ用の事前準備）](#第2部-デプロイ用の事前準備任意) へ進む。デプロイしない場合は [README の「トレーニング手順」](../README.md#トレーニング手順) に戻り、パイプラインの作成・実行へ進む。

---

# 第2部. デプロイ用の事前準備（任意）

> この第2部は、ビルドしたアプリを Azure 上で動かして脆弱性を手動確認したい場合のみ実施する。デプロイを行わなくても、CI/CD パイプラインの実行とスキャン結果の確認は可能。

パイプラインの `Deploy` ステージは、ビルドしたコンテナイメージを **Azure Container Registry** に push し、**Azure App Service**（Linux コンテナー）にデプロイする。これらの Azure リソースとサービス接続は**パイプラインでは自動作成されない**ため、事前に手動で用意する。

ここでは、Azure Portal と Azure DevOps の GUI 操作でリソースを作成し、作成した値を [`azure-pipelines.yml`](../azure-pipelines.yml) のどの変数に反映するかまでを説明する。

## 全体像

```text
[Azure Portal]                          [Azure DevOps]
 1. リソースグループ                      4. サービス接続(ARM)
 2. Azure Container Registry  ──────┐     5. パイプライン変数へ反映
 3. Azure App Service               │
       │                            │
       └── サービスプリンシパルに ───┘
            AcrPush / Contributor を付与
```

## 準備するもの一覧

| # | リソース／設定 | 作成場所 | 反映先（パイプライン変数など） |
|---|----------------|----------|-------------------------------|
| 1 | リソースグループ | Azure Portal | （変数には直接反映しない。下記リソースの入れ物） |
| 2 | Azure Container Registry | Azure Portal | ログインサーバー → `acrLoginServer` |
| 3 | Azure App Service（Linux コンテナー） | Azure Portal | アプリ名 → `webAppName` |
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

## 3. Azure App Service（Linux コンテナー）の作成（Azure Portal）

1. 検索ボックスに「App Services」と入力し、**App Services** を開く。
2. **作成** > **Web アプリ** をクリックする。
3. **基本** タブで次を入力する。
   - **サブスクリプション** / **リソース グループ**: 手順 1 で作成したもの
   - **名前**: グローバルに一意な名前（例: `app-devsecops-training`）。これが URL `https://<名前>.azurewebsites.net` になる。
   - **発行**: **コンテナー**
   - **オペレーティング システム**: **Linux**
   - **地域**: 手順 1 と同じリージョン
   - **Linux プラン / 価格プラン**: 任意（教材用途では `B1` など）
4. **次へ: データベース** > **次へ: コンテナー** と進み、**コンテナー** タブでいったん任意の公開イメージ（例: `nginx`）を指定するか、既定のまま進める。
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
5. **App registration (automatic)** を選び、資格情報（credential）に **Workload identity federation** が選択された状態にする（推奨方式）。資格情報には **Secret** も選べるが、シークレットのローテーション管理が不要な Workload identity federation が推奨される。
6. 次を選択・入力する。
   - **Scope level**: **Subscription**
   - **Subscription**: 対象サブスクリプション
   - **Resource group**: 手順 1 で作成したリソースグループ（任意。絞り込むと安全）
   - **Service connection name**: 任意の名前（例: `sc-devsecops-training`）
   - **Grant access permission to all pipelines**: 教材では有効（本番では非推奨。パイプラインごとに個別認可することが望ましい）
7. **Save** をクリックする。

> この **Service connection name** を、後でパイプライン変数 `azureServiceConnection` に設定する。
> 自動作成方式では、対応するサービスプリンシパル（またはマネージド ID）が Microsoft Entra ID に作成される。次の手順 5 でこの ID にロールを付与する。
> 参考: [Azure Resource Manager サービス接続](https://learn.microsoft.com/azure/devops/pipelines/library/connect-to-azure)

---

## 5. RBAC ロールの割り当て（Azure Portal）

手順 4 で作成されたサービスプリンシパル（サービス接続が使う ID）に、Azure Container Registry への push と Azure App Service へのデプロイの権限を付与する。

### 5-1. サービス接続が使う ID の名前を確認する

1. Azure DevOps の **Project settings** > **Service connections** で、手順 4 のサービス接続を開く。
2. **Manage Service Principal**（または接続詳細）のリンクから、Microsoft Entra ID 上のアプリ（サービスプリンシパル）の名前・アプリケーション ID を控える。

### 5-2. Azure Container Registry に AcrPush を付与する

1. Azure Portal で手順 2 の Azure Container Registry を開く。
2. 左メニューの **アクセス制御 (IAM)** を開く。
3. **追加** > **ロールの割り当ての追加** をクリックする。
4. **ロール** タブで **AcrPush** を選択する。
5. **メンバー** タブで **+ メンバーを選択する** をクリックし、5-1 で確認したサービスプリンシパルを選ぶ。
6. **レビューと割り当て** をクリックする。

### 5-3. Azure App Service（またはリソースグループ）に Contributor を付与する

1. Azure Portal で手順 3 の Azure App Service、または手順 1 のリソースグループを開く。
2. **アクセス制御 (IAM)** > **追加** > **ロールの割り当ての追加** をクリックする。
3. **ロール** タブで **共同作成者（Contributor）** を選択する。
4. **メンバー** タブで同じサービスプリンシパルを選ぶ。
5. **レビューと割り当て** をクリックする。

> 最小権限を重視する場合は、Contributor の代わりに **Website Contributor** を Azure App Service に付与してもよい。
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
| Azure Container Registry のログインサーバー（手順 2-5） | `acrLoginServer` | `acrdevsecopstraining.azurecr.io` |
| Azure App Service（Web アプリ）の名前（手順 3） | `webAppName` | `app-devsecops-training` |
| サービス接続の名前（手順 4） | `azureServiceConnection` | `sc-devsecops-training` |
| デプロイ有効化 | `DEPLOY_TO_AZURE` | `true` |

> 一時的に 1 回だけデプロイしたい場合は、YAML を編集せず、パイプライン実行画面の **Run pipeline** > **Variables** で同名の変数を上書きしてもよい。

---

## 7. デプロイの実行と確認

1. 変数を設定したうえでパイプラインを実行する。
2. `Deploy` ステージが成功すると、Azure Container Registry へ push され Azure App Service にデプロイされる。
3. ブラウザで `https://<webAppName>.azurewebsites.net` を開き、アプリが表示されることを確認する。

うまくいかない場合は次を確認する。

- `Deploy` ステージがスキップされる → `DEPLOY_TO_AZURE` が `true` か、各変数が空でないか。
- Azure Container Registry への push が失敗する → サービスプリンシパルに **AcrPush** が付与されているか、`acrLoginServer` が正しいか。
- Azure App Service へのデプロイが失敗する → サービスプリンシパルに **Contributor**（または Website Contributor）が付与されているか、`webAppName` が正しいか。
- ページが表示されない → Azure App Service の **ログ ストリーム** でコンテナ起動ログを確認する。アプリはコンテナ内で 5000 番ポートを使用する。

> 🛑 **デプロイした `https://<webAppName>.azurewebsites.net` は既定でインターネットに公開される。** 本アプリは意図的に脆弱なため、動作確認が済んだら速やかに削除する（[後片付け](#後片付け)）か、確認中も残す場合は次の手順 8 で **自分の IP のみ許可** に制限すること。

---

## 8. アクセスを自分の IP のみに制限する（強く推奨）

脆弱なアプリをインターネットに公開したまま放置すると、攻撃者や自動スキャンの標的になる。確認作業中にアプリを残す場合は、Azure App Service の **アクセス制限**（ネットワークの受信規則）で**自分のグローバル IP からのアクセスのみを許可**する。許可ルールを 1 つ追加すると、それ以外の送信元は暗黙的に「すべて拒否」になる。

1. 自分のグローバル IP アドレスを確認する（例: 検索エンジンで「what is my ip」を検索）。社内プロキシ・NAT・VPN 経由の場合は、その**出口（egress）IP** になる点に注意する（例: `203.0.113.45`）。
2. [Azure Portal](https://portal.azure.com) で対象の Azure App Service（手順 3 の Web アプリ）を開く。
3. 左側のメニューで **[設定]** > **[ネットワーク]** を選択する。
4. **[ネットワーク]** ウィンドウの **[受信トラフィックの構成]** で **[パブリック ネットワーク アクセス]** を選択する。
5. **[アクセス制限]** ウィンドウで **[追加]** を選択する。
6. **[アクセス制限の追加]** ペインで次を入力する。
   - **[アクション]**: **[許可]**
   - 名前（省略可。例: `allow-my-ip`）
   - **[優先度]**: 任意の数値（例: `100`）
   - **[種類]**: **[IPv4]**（IPv6 のみの環境では **[IPv6]**）
   - **IP アドレス ブロック**: 自分の IP を CIDR 表記で指定する。単一 IP は `/32` を付ける（例: `203.0.113.45/32`）。
   - **[ルールの追加]** を選択する。
7. **[アクセス制限]** ウィンドウで **[保存]** を選択する。保存するまでルールは有効にならない。
8. 別ネットワークや VPN OFF など、許可していない経路からアプリにアクセスし、**HTTP 403** で拒否されることを確認する。許可した IP からはこれまでどおりアクセスできる。

> 接続経路が変わる（再接続・VPN 切替・拠点移動など）と出口 IP も変わり、自分自身もアクセスできなくなることがある。その場合はルールの **IP アドレス ブロック** を現在の IP に更新する。
> 参考: [Azure App Service のアクセス制限を設定する](https://learn.microsoft.com/azure/app-service/app-service-ip-restrictions)

---

## 後片付け

教材の確認が終わったら、**脆弱なアプリを公開したまま残さないため**、そして不要な課金を避けるためにリソースを削除する。最も簡単なのは手順 1 のリソースグループごと削除する方法である。

1. Azure Portal で手順 1 のリソースグループを開く。
2. 上部の **リソース グループの削除** をクリックし、確認のため名前を入力して削除する。
