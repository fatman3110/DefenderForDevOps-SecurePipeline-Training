# 事前準備ガイド

本ガイドは、本教材を実行するための事前準備を 2 部構成で説明する。

- **[第1部. 共通の事前準備（必須）](#第1部-共通の事前準備必須)**: パイプラインを動かすための土台となる Azure DevOps 組織・プロジェクトを用意する。デプロイの有無にかかわらず必要。
- **[第2部. デプロイ用の事前準備（任意）](#第2部-デプロイ用の事前準備任意)**: ビルドしたアプリを Azure にデプロイして動作確認したい場合のみ必要。Azure Container Registry / Azure App Service / サービス接続を用意する。

> 画面名・メニュー位置・ボタン名は変更される可能性がある。最新の手順は各公式ドキュメントを参照すること。

---

# 第1部. 共通の事前準備（必須）

パイプラインを実行するには、Azure DevOps の**組織**と、その中の**プロジェクト**が必要になる。すでに利用できる組織・プロジェクトがある場合はこの第1部を読み飛ばしてよい。

## A. Azure DevOps 組織の作成

1. [Azure Portal](https://portal.azure.com) を開き、Microsoft アカウントまたは職場・学校アカウントでサインインする。
2. 画面左上の **アプリ ランチャー**（グリッド状のアイコン ⊞）をクリックし、**DevOps** を選択する。
   - Azure DevOps の画面（`https://dev.azure.com`）に遷移する。
3. **Create new organization**（新しい組織の作成）を選択し、画面の案内に従って進める。
4. 組織名（例: `myorg-devsecops`）とホストするリージョンを指定し、作成する。

> 参考: [Azure DevOps へのサインアップ](https://learn.microsoft.com/azure/devops/user-guide/sign-up-invite-teammates) / [組織の作成](https://learn.microsoft.com/azure/devops/organizations/accounts/create-organization)

## B. プロジェクトの作成

1. 作成した組織のトップページで **+ New project**（新しいプロジェクト）をクリックする。もしくは、組織を新規作成した場合、そのまま新規プロジェクト作成画面に移行している。
2. 次を入力する。
   - **Project name**: 任意の名前（例: `DevSecOps-Training`）
   - **Visibility**: **Private**（教材用途では非公開を推奨）
   - **Version control**: **Git**
3. **Create** をクリックする。

> 参考: [プロジェクトの作成](https://learn.microsoft.com/azure/devops/organizations/projects/create-project)

## C. コードのプッシュ

作成したプロジェクトの **Repos** に本教材一式（このリポジトリの内容）を取り込む。Azure Repos の **インポート機能**を使えば、ローカル操作なしでソースの URL を指定するだけで丸ごとコピーできる。

1. Azure DevOps でプロジェクトを開き、**Repos** > **Files** を開く。
2. **Import repository** を選択する。
3. **Source type** に **Git** を選び、**Clone URL** に取り込み元のクローン URL を入力する。
4. **Import** をクリックする。完了すると Azure Repos に全ブランチ・全コミットがコピーされる。

> 参考: [Git リポジトリをインポートする](https://learn.microsoft.com/azure/devops/repos/git/import-git-repository)

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
5. **レビューと作成** > **作成** をクリックする。

> 参考: [リソース グループの管理](https://learn.microsoft.com/azure/azure-resource-manager/management/manage-resource-groups-portal)

---

## 2. Azure Container Registry の作成（Azure Portal）

1. 検索ボックスに「Container registries」と入力し、**Container registries** を開く。
2. **作成** をクリックする。
3. **基本** タブで次を入力する。
   - **サブスクリプション** / **リソース グループ**: 手順 1 で作成したもの
   - **レジストリ名**: グローバルに一意な名前（例: `acrdevsecopstraining`）。英数字のみ。
   - **場所**: 手順 1 と同じリージョン
   - **ドメイン名ラベルのスコープ**: **セキュリティ保護なし**（教材用途では十分）
   - **価格プラン（SKU）**: `Basic`（教材用途では十分）
   - **ロールの割り当てアクセス許可モード**: 既定の **RBAC レジストリのアクセス許可** 
5. 作成後、レジストリのリソースを開き、**概要** に表示される **ログイン サーバー**（例: `acrdevsecopstraining.azurecr.io`）を控える。

> この **ログイン サーバー** の値を、後でパイプライン変数 `acrLoginServer` に設定する。
> 参考: [コンテナー レジストリの作成](https://learn.microsoft.com/azure/container-registry/container-registry-get-started-portal)

---

## 3. Azure App Service（Linux コンテナー）の作成（Azure Portal）

1. 検索ボックスに「App Services」と入力し、**App Services** を開く。
2. **作成** > **Web アプリ** をクリックする。
3. **基本** タブで次を入力する。
   - **サブスクリプション** / **リソース グループ**: 手順 1 で作成したもの
   - **名前**: グローバルに一意な名前（例: `app-devsecops-training`）。これがリソース名になり、後でパイプライン変数 `webAppName` に設定する。アクセス URL は、この名前にランダムな文字列とリージョンが付いた形式（例: `https://app-devsecops-training-xxxxxxxx.japaneast-01.azurewebsites.net`）になり、作成後の **概要** で確認できる。
   - **発行**: **コンテナー**
   - **オペレーティング システム**: **Linux**
   - **地域**: 手順 1 と同じリージョン。手順書通りなら、**Japan East**
   - **価格プラン**: 教材用途ではコスト最小の **Basic `B1`** を指定
4. **次: データベース** > **次: コンテナー** と進み、**コンテナー** タブは既定のまま進める。
   - **コンテナー** タブは、**イメージ ソース**（Azure Container Registry など）・**イメージ**・**タグ** を指定する画面。ここで実際のアプリイメージを指定できるが、本教材ではイメージはパイプラインから後で push・デプロイするため、ここでは既定のまま進めてよい。
5. **確認および作成** > **作成** をクリックする。
6. 作成後、Web アプリの **概要** に表示される **既定のドメイン**（例: `app-devsecops-training-xxxxxxxx.japaneast-01.azurewebsites.net` のように、名前にランダムな文字列とリージョンが付く形式）を控える。動作確認時はこの URL でアクセスする。

> この Web アプリの **名前** を、後でパイプライン変数 `webAppName` に設定する。
> 参考: [カスタム コンテナーを Azure に対して実行する](https://learn.microsoft.com/azure/app-service/quickstart-custom-container)

> **補足: 作成時に「quota」エラーが出る場合**
> App Service プラン（`Basic B1` など）は専用 VM を消費するため、サブスクリプション／リージョンの VM 枠が `0` だと `Operation cannot be completed without additional quota`（`Current Limit (Total VMs): 0`）というエラーで失敗する。次のいずれかで対処する。
> 1. **別リージョンで作り直す**（最も手軽。例: `East US` など別の地域を選ぶ）。
> 2. **クォータ増加を申請する**:
>    1. [Azure Portal](https://portal.azure.com) の検索ボックスで「**クォータ**」を開く。
>    2. プロバイダー一覧から **App Service** を選ぶ。
>    3. 上部フィルターで**サブスクリプション**と**リージョン**（App Service を作った場所）を選ぶ。
>    4. 対象 SKU の枠（`Basic B1` なら **Basic VMs**）の行で **鉛筆アイコン** をクリックし、新しい上限値（`2`〜`3` 推奨）を入力 → **送信**。数分でレビューされる。
> 参考: [クォータ増加を申請する](https://learn.microsoft.com/azure/quotas/quickstart-increase-quota-portal)

---

## 4. Azure Resource Manager サービス接続の作成（Azure DevOps）

パイプラインから Azure を操作するための接続を作成する。

1. Azure DevOps でプロジェクトを開き、左下の **Project settings**（プロジェクト設定）をクリックする。
2. **Pipelines** > **Service connections** を開く。
3. **Create service connection** をクリックする。
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

1. Azure DevOps の **Project settings** > **Service connections** で、手順 4 のサービス接続を開く（**Overview** タブが表示される）。
2. **Details** にある **Manage App registration** のリンクをクリックすると、Microsoft Entra ID 上のアプリ登録ページが開く。表示される **アプリ名（表示名）** と **アプリケーション (クライアント) ID** を控える。


### 5-2. Azure Container Registry に AcrPush を付与する

1. Azure Portal で手順 2 の Azure Container Registry を開く。
2. 左メニューの **アクセス制御 (IAM)** を開く。
3. **追加** > **ロールの割り当ての追加** をクリックする。
4. **ロール** タブで **AcrPush** を選択する。
5. **メンバー** タブで **+ メンバーを選択する** をクリックし、検索ボックスに **5-1 で控えたアプリ名（表示名）** または **アプリケーション (クライアント) ID** を貼り付けて検索し、表示されたサービスプリンシパルを選ぶ。
   - 自動作成方式の表示名は `sc-devsecops-training` ではなく `<組織名>-<プロジェクト名>-<GUID>` のような形式になる。名前の一部で曖昧に検索すると対象が検出できないことがあるため、**正確な表示名か ID で検索**すること。
6. **レビューと割り当て** をクリックする。

### 5-3. Azure App Service に Website Contributor を付与する

デプロイで必要なのは「既存の Web アプリ（App Service）へのコード/コンテナ配置」だけなので、サブスクリプション全体を操作できる **共同作成者（Contributor）** ではなく、Web アプリ操作に限定された **Website Contributor** を、**Web アプリ単体のスコープ**に付与する（最小権限）。

1. Azure Portal で手順 3 の Azure App Service（Web アプリ）を開く。
2. **アクセス制御 (IAM)** > **追加** > **ロールの割り当ての追加** をクリックする。
3. **ロール** タブで **Web サイト共同作成者** を選択する。
4. **メンバー** タブで、5-2 と同じサービスプリンシパルを（表示名または **アプリケーション (クライアント) ID** で検索して）選ぶ。
5. **レビューと割り当て** をクリックする。

> 参考: [Website Contributor / Web Plan Contributor（組み込みロール）](https://learn.microsoft.com/azure/role-based-access-control/built-in-roles/web-and-mobile)

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

> 一時的に 1 回だけデプロイしたい場合は、YAML を編集せず、パイプライン実行画面の **Run pipeline** > **Variables** で同名の変数を上書きしてもよい。

---

## 7. デプロイの実行と確認

1. 変数を設定したうえでパイプラインを実行する。
2. `Deploy` ステージが成功すると、Azure Container Registry へ push され Azure App Service にデプロイされる。
3. ブラウザで Web アプリの **既定のドメイン**（手順 3 の手順 6 で控えた、`https://app-devsecops-training-xxxxxxxx.japaneast-01.azurewebsites.net` のような URL）を開き、アプリが表示されることを確認する。

うまくいかない場合は次を確認する。

- `Deploy` ステージがスキップされる → `DEPLOY_TO_AZURE` が `true` か、各変数が空でないか。
- Azure Container Registry への push が失敗する → サービスプリンシパルに **AcrPush** が付与されているか、`acrLoginServer` が正しいか。
- Azure App Service へのデプロイが失敗する → サービスプリンシパルに **Contributor**（または Website Contributor）が付与されているか、`webAppName` が正しいか。
- ページが表示されない → Azure App Service の **ログ ストリーム** でコンテナ起動ログを確認する。アプリはコンテナ内で 5000 番ポートを使用する。

> 🛑 **デプロイした Web アプリの既定ドメイン（手順 3 で控えた URL）は既定でインターネットに公開される。** 本アプリは意図的に脆弱なため、動作確認が済んだら速やかに削除する（[後片付け](#後片付け)）か、確認中も残す場合は次の手順 8 で **自分の IP のみ許可** に制限すること。

---

## 8. アクセスを自分の IP のみに制限する（強く推奨）

脆弱なアプリをインターネットに公開したまま放置すると、攻撃者や自動スキャンの標的になる。確認作業中にアプリを残す場合は、Azure App Service の **アクセス制限**（ネットワークの受信規則）で**自分のグローバル IP からのアクセスのみを許可**する。許可ルールを 1 つ追加すると、それ以外の送信元は暗黙的に「すべて拒否」になる。

1. 自分のグローバル IP アドレスを確認する（例: 検索エンジンで「what is my ip」を検索）。
2. [Azure Portal](https://portal.azure.com) で対象の Azure App Service（手順 3 の Web アプリ）を開く。
3. 左側のメニューで **[設定]** > **[ネットワーク]** を選択し、**[受信トラフィック]** の **[公衆ネットワーク アクセス]**を開く。**アクセス制限** の画面が表示される。
4. **[アプリのアクセス]** の **[公衆ネットワーク アクセス]** で **[選択した仮想ネットワークと IP アドレスから有効]** を選択する。
5. **[サイトのアクセスとルール]** で **[メインサイト]** タブが選択されていることを確認する。**[一致しないルールのアクション]** を **[拒否]** に設定する。
6. **[+ 追加]** を選択し、右側に開く **[規則の追加]** ペインで次を入力する。
   - **[名前]**: 任意（例: `allow-my-ip`）
   - **[アクション]**: **[許可]**
   - **[優先度]**: 任意の数値（例: `100`）
   - **[説明]**: 省略可
   - **[ソースの設定]** の **[種類]**: **[IPv4]**（IPv6 のみの環境では **[IPv6]**）
   - **[IP アドレス ブロック]**: 自分の IP を CIDR 表記で指定する。単一 IP は `/32` を付ける（例: `203.0.113.45/32`）。
   - **HTTP ヘッダーのフィルター設定**（X-Forwarded-For など）は、特に必要なければ空のままでよい。
7. ペイン下部の **[規則の追加]** を選択して、ルールを一覧に追加する。
8. 画面上部の **[保存]** を選択する。

> 接続経路が変わる（再接続・VPN 切替・拠点移動など）と出口 IP も変わり、自分自身もアクセスできなくなることがある。その場合はルールの **IP アドレス ブロック** を現在の IP に更新する。
> 参考: [Azure App Service のアクセス制限を設定する](https://learn.microsoft.com/azure/app-service/app-service-ip-restrictions)

---

## 後片付け

教材の確認が終わったら、**脆弱なアプリを公開したまま残さないため**、そして不要な課金を避けるためにリソースを削除する。最も簡単なのは手順 1 のリソースグループごと削除する方法である。

1. Azure Portal で手順 1 のリソースグループを開く。
2. 上部の **リソース グループの削除** をクリックし、確認のため名前を入力して削除する。
