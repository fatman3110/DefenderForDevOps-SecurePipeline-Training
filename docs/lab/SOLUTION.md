# 解答（SOLUTION）

各脆弱性の修正方法を示す。修正後は単体テストを実行し、機能の回帰がないことを確認すること。

---

## #1 ハードコードされた認証情報

シークレットをソースコードから排除し、 Azure Key Vault に保管して実行時に取得する。アプリには接続情報をハードコードせず、`DefaultAzureCredential`（Azure App Service のマネージド ID）で Key Vault に認証し、`SecretClient` でシークレットを読み出す。これによりコード・リポジトリにも環境変数にも平文を残さず、シークレットのローテーションやアクセス監査を Key Vault 側で一元管理できる。

> 参考:
> - [Azure Key Vault の基本概念](https://learn.microsoft.com/azure/key-vault/general/basic-concepts)
> - [Key Vault シークレットを Python で取得する（azure-keyvault-secrets）](https://learn.microsoft.com/azure/key-vault/secrets/quick-create-python)
> - [DefaultAzureCredential によるパスワードレス認証](https://learn.microsoft.com/azure/developer/python/sdk/authentication/credential-chains)
> - [App Service でマネージド ID を使う](https://learn.microsoft.com/azure/app-service/overview-managed-identity)

**修正前**

```python
app.config["SECRET_KEY"] = "hardcoded-super-secret-key-do-not-use-1234567890"
DB_PASSWORD = "P@ssw0rd-Hardcoded-2024"
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

**修正後**

```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Key Vault の URI のみコード外（アプリ設定の環境変数）から渡す。シークレット自体は保持しない。
KEY_VAULT_URI = os.environ["KEY_VAULT_URI"]  # 例: https://<vault-name>.vault.azure.net/

# マネージド ID（ローカル開発では Azure CLI ログイン等）で Key Vault に認証する。
credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url=KEY_VAULT_URI, credential=credential)

# 実行時に Key Vault からシークレットを取得する。
app.config["SECRET_KEY"] = secret_client.get_secret("app-secret-key").value
DB_PASSWORD = secret_client.get_secret("db-password").value
AWS_ACCESS_KEY_ID = secret_client.get_secret("aws-access-key-id").value
AWS_SECRET_ACCESS_KEY = secret_client.get_secret("aws-secret-access-key").value
```

> シークレットの値ではなく **Key Vault の URI だけ**をアプリ設定で渡す点がポイント。Key Vault へのアクセスに使う SDK（認証用の `azure-identity`、シークレット取得用の `azure-keyvault-secrets`）が必要なので `requirements.txt` に両方を追加し、App Service のマネージド ID に Key Vault の **Key Vault シークレット ユーザー** ロール（または get/list アクセスポリシー）を付与しておくこと。

---

## #2 HttpOnly のない Cookie

Cookie に `httponly` / `secure` / `samesite` 属性を付与する。

**修正前**

```python
resp.set_cookie(
    "user_session",
    str(user["id"]),
    httponly=False,
    secure=False,
)
```

**修正後**

```python
resp.set_cookie(
    "user_session",
    str(user["id"]),
    httponly=True,
    secure=True,
    samesite="Lax",
)
```

`httponly=True` で JavaScript からの読み取りを防ぎ、`secure=True` で HTTPS のみ送信、`samesite="Lax"` で CSRF を緩和する。

---

## #3 古い脆弱なライブラリ

依存ライブラリを脆弱性が修正されたバージョンに更新する。

**修正前**

```text
Flask==2.0.1
Werkzeug==2.0.1
Jinja2==3.0.0
itsdangerous==2.0.1
MarkupSafe==2.0.1
gunicorn==20.1.0
```

**修正後**（例: 更新時点の安定版に固定する）

```text
Flask>=3.0.3
Werkzeug>=3.0.3
Jinja2>=3.1.4
itsdangerous>=2.2.0
MarkupSafe>=2.1.5
gunicorn>=22.0.0
```

更新後は pip-audit（および Microsoft Security DevOps 有効時は Trivy）を再実行し、CVE が解消されたことを確認する。バージョンは演習時点の最新安定版を確認して指定すること。

---

## #4 クロスサイトスクリプティング（XSS）

ユーザー入力を文字列連結で HTML に埋め込まず、自動エスケープされるテンプレートを使う。

**修正前**

```python
query = request.args.get("q", "")
template = (
    "<!doctype html>...<p>検索ワード: " + query + "</p>..."
)
return render_template_string(template)
```

**修正後**

```python
query = request.args.get("q", "")
return render_template("search.html", query=query)
```

`search.html`（Jinja2 の自動エスケープが有効）

```html
<p>検索ワード: {{ query }}</p>
```

入力を変数としてテンプレートに渡すことで、`{{ query }}` が自動的にエスケープされる。ユーザー入力を `render_template_string` のテンプレート本文に連結しないこと。

---

## #5 アクセスコントロールの脆弱性（IDOR）

リクエストされた `user_id` がログイン中のユーザーと一致するかを検証する。

**修正前**

```python
@app.route("/profile/<int:user_id>")
def profile(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    target_user = USERS.get(user_id)
    if not target_user:
        return "ユーザーが見つかりません。", 404
    return render_template("profile.html", profile_user=target_user)
```

**修正後**

```python
@app.route("/profile/<int:user_id>")
def profile(user_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    # 認可チェック: 自分のプロフィールのみ閲覧可能
    if session["user_id"] != user_id:
        return "アクセスが拒否されました。", 403
    target_user = USERS.get(user_id)
    if not target_user:
        return "ユーザーが見つかりません。", 404
    return render_template("profile.html", profile_user=target_user)
```

認証（ログイン済みか）だけでなく、認可（そのリソースにアクセスする権限があるか）を必ず確認する。
