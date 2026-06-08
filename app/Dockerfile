# 脆弱性 #3 の一部: 古いベースイメージを意図的に使用している。
# Trivy がベースイメージの OS パッケージ脆弱性を検出する。
# 本番では最新のパッチ適用済みイメージを使用すべき。
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# gunicorn でアプリを起動する
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
