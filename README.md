# RepoSage

GitHubリポジトリのソースコードを分析し、包括的なマークダウン形式のドキュメントを自動生成するツールです。

## 機能

- GitHubリポジトリの基本情報取得
- ファイル構造の解析と視覚化
- ソースコードの分析とフィルタリング
- マークダウン形式のドキュメント生成
- HTML形式への変換オプション
- 無視パターンによるファイルフィルタリング
- 大規模リポジトリの再帰的な取得と処理

## 使い方

1. リポジトリURLを入力（例: `https://github.com/username/repo`）
2. 必要に応じて最大深度を設定（-1は無制限）
3. 必要に応じて無視パターンを設定（デフォルトで一般的なパターンが設定済み）
4. 「ドキュメント生成」ボタンをクリック
5. 生成されたマークダウンをコピーまたはダウンロード

## 無視パターンの設定

### ファイル無視パターン
特定のファイルやディレクトリをドキュメントから除外します。
例:
```
node_modules/
.git/
*.log
```

### ソースコード内無視パターン
ソースコード内の特定の行をフィルタリングします。
例:
```
// TODO:
# FIXME:
* @ts-ignore
```

## 環境設定

```bash
# 必要なパッケージのインストール
pip install -r requirements.txt

# 環境変数の設定（オプション）
# .env ファイルに GITHUB_TOKEN を設定するか、以下のように環境変数を設定
export GITHUB_TOKEN=your_github_token

# アプリケーションの起動
python main.py
```

## GitHub API トークンについて

GitHub API トークンは必須ではありませんが、設定することで以下の利点があります：

- API レート制限の緩和（認証なしは60リクエスト/時間、認証ありは5000リクエスト/時間）
- プライベートリポジトリへのアクセス
- より詳細なリポジトリ情報の取得
- 大規模リポジトリの完全な取得

トークンがない場合でも基本的な機能は使用できますが、一部の情報が制限される場合があります。

### トークンの取得方法

1. GitHubにログイン
2. 右上のプロフィールアイコン → Settings
3. 左メニューの「Developer settings」
4. 「Personal access tokens」→「Tokens (classic)」
5. 「Generate new token」→「Generate new token (classic)」
6. 少なくとも「repo」スコープにチェック
7. トークンを生成し、`.env`ファイルに`GITHUB_TOKEN=your_token_here`として保存

## エラー対応

### 'NoneType' object has no attribute 'get' エラー
このエラーは主に以下の原因で発生します：
- 無効なリポジトリURL
- APIレート制限に達した
- ネットワーク接続の問題

対処法：
- リポジトリURLが正しいか確認
- GitHub API トークンを設定
- しばらく待ってから再試行

### 大きなリポジトリの処理
大規模なリポジトリの場合、GitHub APIの制限により完全なツリーを一度に取得できないことがあります。
RepoSageは自動的に代替方法でファイルを取得しますが、処理に時間がかかる場合があります。

## Hugging Face Spaces での実行

このアプリケーションは Hugging Face Spaces で実行できます。
Spaces の設定で GITHUB_TOKEN を環境変数として設定することをお勧めします（必須ではありません）。

## ライセンス

MITライセンス 