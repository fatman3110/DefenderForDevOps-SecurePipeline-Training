# 解答（SOLUTION）

各脆弱性の修正方法を示す。修正後は単体テストを実行し、機能の回帰がないことを確認すること。

---

## #1 ハードコードされた認証情報

シークレットをソースコードから排除し、 Azure Key Vault 等のシークレットストレージから取得する。下記の修正例ではアプリは環境変数経由で認証情報を受け取り、実際の値は Azure Key Vault に保管して Azure App Service のアプリ設定で Key Vault 参照として注入する（コード・リポジトリに平文を残さない）。

> 参考:
> - [Azure Key Vault の基本概念](https://learn.microsoft.com/azure/key-vault/general/basic-concepts)
> - [App Service と Azure Functions で Key Vault 参照を使用する](https://learn.microsoft.com/azure/app-service/app-service-key-vault-references)
> - [Key Vault シークレットを Python で取得する（azure-keyvault-secrets）](https://learn.microsoft.com/azure/key-vault/secrets/quick-create-python)

**修正前**

```python
app.config["SECRET_KEY"] = "hardcoded-super-secret-key-do-not-use-1234567890"
DB_PASSWORD = "P@ssw0rd-Hardcoded-2024"
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

**修正後**

```python
import os

app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
DB_PASSWORD = os.environ.get("DB_PASSWORD")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
```

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
