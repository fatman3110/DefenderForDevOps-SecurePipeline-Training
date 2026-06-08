"""
DefenderForDevOps セキュアパイプライン トレーニング - 脆弱な Flask アプリケーション

警告: このアプリは意図的にセキュリティ脆弱性を含む。教育・トレーニング目的でのみ使用し、
      本番環境では使用しないこと。

含まれる脆弱性:
    #1 ハードコードされた認証情報（ダミー）
    #2 HttpOnly のない Cookie
    #3 古い脆弱なライブラリ（requirements.txt）
    #4 クロスサイトスクリプティング（XSS / 反射型）
    #5 アクセスコントロールの脆弱性（IDOR: /profile/<user_id>）
"""
from flask import (
    Flask,
    request,
    render_template,
    render_template_string,
    redirect,
    url_for,
    make_response,
    session,
)

app = Flask(__name__)

# ============================================================
# 脆弱性 #1: ハードコードされた認証情報（ダミー）
# シークレットキー・DB パスワード・API キーをソースコードに直書きしている。
# Gitleaks / Bandit が検出する。本来は環境変数や Key Vault から取得すべき。
# ============================================================
app.config["SECRET_KEY"] = "hardcoded-super-secret-key-do-not-use-1234567890"
DB_PASSWORD = "P@ssw0rd-Hardcoded-2024"  # noqa: S105
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"  # AWS 公式ドキュメントの例示値（ダミー）
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"  # ダミー


# ============================================================
# ダミーのユーザーデータストア（DB 接続なし・インメモリ）
# 本来は DB に保存し、パスワードはハッシュ化して保管すべき。
# ============================================================
USERS = {
    1: {
        "id": 1,
        "username": "alice",
        "password": "alice-password",
        "display_name": "Alice Anderson",
        "email": "alice@example.com",
        "ssn": "123-45-6789",
        "salary": "$85,000",
    },
    2: {
        "id": 2,
        "username": "bob",
        "password": "bob-password",
        "display_name": "Bob Brown",
        "email": "bob@example.com",
        "ssn": "987-65-4321",
        "salary": "$92,000",
    },
}


def find_user_by_credentials(username, password):
    """ユーザー名・パスワードで認証する（平文比較・教材簡略化）。"""
    for user in USERS.values():
        if user["username"] == username and user["password"] == password:
            return user
    return None


@app.route("/")
def index():
    """トップページ。ログイン状態を表示する。"""
    current_user_id = session.get("user_id")
    current_user = USERS.get(current_user_id) if current_user_id else None
    return render_template("index.html", user=current_user)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    ログイン処理。

    脆弱性 #2: HttpOnly のない Cookie
    認証後に発行する Cookie に httponly=False を指定しているため、JavaScript
    （document.cookie）から読み取れてしまう。XSS と組み合わせるとセッション窃取に
    つながる。本来は httponly=True, secure=True, samesite='Lax' を指定すべき。
    """
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = find_user_by_credentials(username, password)
        if user:
            session["user_id"] = user["id"]
            resp = make_response(redirect(url_for("profile", user_id=user["id"])))
            resp.set_cookie(
                "user_session",
                str(user["id"]),
                httponly=False,
                secure=False,
            )
            return resp
        error = "ユーザー名またはパスワードが正しくありません。"
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    """ログアウト処理。"""
    session.clear()
    resp = make_response(redirect(url_for("index")))
    resp.delete_cookie("user_session")
    return resp


@app.route("/profile/<int:user_id>")
def profile(user_id):
    """
    プロフィール表示。

    脆弱性 #5: アクセスコントロールの脆弱性（IDOR）
    ログインさえしていれば、URL の <user_id> を書き換えるだけで他人のプロフィール
    （SSN・給与などの機密情報）が閲覧できてしまう。リクエストされた user_id と
    ログイン中のユーザーが一致するかの認可チェックが欠落している。
    """
    if "user_id" not in session:
        return redirect(url_for("login"))

    target_user = USERS.get(user_id)
    if not target_user:
        return "ユーザーが見つかりません。", 404

    return render_template("profile.html", profile_user=target_user)


@app.route("/search")
def search():
    """
    検索ページ。

    脆弱性 #4: クロスサイトスクリプティング（XSS / 反射型）
    クエリパラメータ q をエスケープせずに render_template_string でそのまま HTML に
    埋め込んでいるため、スクリプトが実行される。
    例: /search?q=<script>alert(document.cookie)</script>
    """
    query = request.args.get("q", "")
    template = (
        "<!doctype html><html><head><title>検索結果</title></head><body>"
        "<h1>検索結果</h1>"
        "<p>検索ワード: " + query + "</p>"
        '<p><a href="/">トップへ戻る</a></p>'
        "</body></html>"
    )
    return render_template_string(template)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)  # noqa: S104,S201
