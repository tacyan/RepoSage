#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RepoSage - GitHubリポジトリ分析ツール

このアプリケーションはGitHubリポジトリのソースコードを分析し、
包括的なマークダウン形式のドキュメントを自動生成します。

主な機能:
- リポジトリ情報の取得
- ファイル構造の解析
- マークダウン形式のドキュメント生成
- 無視パターンによるファイルフィルタリング
"""

import os
import asyncio
import flet as ft
import traceback
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import socket

# 自作モジュールのインポート
from github_api import parseRepoUrl, getDefaultBranch, getRepositoryInfo, getRepositoryContributors, getRepoTree, GITHUB_TOKEN
from file_utils import buildFileTree, shouldIgnore
from markdown_generator import generateRepositoryMarkdown, convertMarkdownToHtml

# 環境変数の読み込み
load_dotenv()

# デフォルトの無視パターン
DEFAULT_IGNORE_PATTERNS = [
    ".git/",
    "node_modules/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".DS_Store",
    "Thumbs.db",
    ".vscode/",
    ".idea/",
    "*.log",
    "dist/",
    "build/",
    "*.min.js",
    "*.min.css"
]

# デフォルトのソースコード内無視パターン
DEFAULT_SOURCE_IGNORE_PATTERNS = [
    "// TODO:",
    "// FIXME:",
    "# TODO:",
    "# FIXME:",
    "/* TODO:",
    "/* FIXME:",
    "* @ts-ignore",
    "# type: ignore",
    "# noqa",
    "# pragma: no cover"
]

class RepoSageApp:
    """
    RepoSage アプリケーションのメインクラス
    """
    
    def __init__(self, page: ft.Page):
        """
        アプリケーションの初期化
        
        @param page - Flet ページオブジェクト
        """
        self.page = page
        self.page.title = "RepoSage - GitHubリポジトリ分析ツール"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.padding = 20
        self.page.scroll = ft.ScrollMode.AUTO
        
        # 状態変数
        self.loading = False
        self.markdown_result = ""
        self.ignore_patterns: List[str] = DEFAULT_IGNORE_PATTERNS.copy()
        self.source_ignore_patterns: List[str] = DEFAULT_SOURCE_IGNORE_PATTERNS.copy()
        
        # UIコンポーネントの初期化
        self.init_ui()
    
    def init_ui(self):
        """
        UIコンポーネントの初期化
        """
        # ヘッダー
        header = ft.Container(
            content=ft.Column([
                ft.Text("RepoSage", size=40, weight=ft.FontWeight.BOLD),
                ft.Text("GitHubリポジトリ分析ツール", size=16)
            ]),
            margin=ft.margin.only(bottom=20)
        )
        
        # GitHub API トークンの警告
        self.token_warning = ft.Container(
            content=ft.Column([
                ft.Text(
                    "警告: GitHub API トークンが設定されていません。一部の機能が制限される可能性があります。",
                    color="orange",
                    weight=ft.FontWeight.BOLD
                ),
                ft.Text(
                    ".env ファイルに GITHUB_TOKEN を設定するか、環境変数として設定してください。",
                    size=12
                )
            ]),
            padding=10,
            border_radius=5,
            bgcolor=ft.colors.AMBER_50,
            visible=not bool(GITHUB_TOKEN),
            margin=ft.margin.only(bottom=20)
        )
        
        # リポジトリURL入力フィールド
        self.repo_url_field = ft.TextField(
            label="GitHubリポジトリURL",
            hint_text="https://github.com/username/repo",
            prefix_icon=ft.icons.LINK,
            expand=True
        )
        
        # 最大深度設定
        self.max_depth_field = ft.TextField(
            label="最大深度 (-1 = 無制限)",
            value="-1",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER
        )
        
        # 無視パターン入力
        self.ignore_patterns_field = ft.TextField(
            label="無視パターン (1行に1パターン)",
            hint_text="node_modules/\n.git/\n*.log",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value="\n".join(DEFAULT_IGNORE_PATTERNS),
            expand=True
        )
        
        # ソースコード内の無視パターン入力
        self.source_ignore_patterns_field = ft.TextField(
            label="ソースコード内の無視パターン (1行に1パターン)",
            hint_text="// TODO:\n// FIXME:\n* @ts-ignore",
            multiline=True,
            min_lines=3,
            max_lines=5,
            value="\n".join(DEFAULT_SOURCE_IGNORE_PATTERNS),
            expand=True
        )
        
        # 出力フォーマット選択
        self.format_dropdown = ft.Dropdown(
            label="出力フォーマット",
            width=150,
            options=[
                ft.dropdown.Option("markdown", "Markdown"),
                ft.dropdown.Option("html", "HTML")
            ],
            value="markdown"
        )
        
        # 生成ボタン
        self.generate_button = ft.ElevatedButton(
            "ドキュメント生成",
            icon=ft.icons.DOCUMENT_SCANNER,
            on_click=self.generate_markdown,
            expand=True
        )
        
        # コピーボタン
        self.copy_button = ft.ElevatedButton(
            "クリップボードにコピー",
            icon=ft.icons.COPY,
            on_click=self.copy_to_clipboard,
            disabled=True,
            expand=True
        )
        
        # ダウンロードボタン
        self.download_button = ft.ElevatedButton(
            "ダウンロード",
            icon=ft.icons.DOWNLOAD,
            on_click=self.download_markdown,
            disabled=True,
            expand=True
        )
        
        # 結果表示エリア
        self.result_text = ft.TextField(
            label="生成されたマークダウン",
            multiline=True,
            read_only=True,
            min_lines=10,
            max_lines=20,
            visible=False,
            expand=True
        )
        
        # プログレスバー
        self.progress_bar = ft.ProgressBar(visible=False)
        
        # 詳細プログレス表示
        self.progress_text = ft.Text("", size=12, italic=True, visible=False)
        
        # ステータステキスト
        self.status_text = ft.Text("", italic=True)
        
        # レイアウト構築
        self.page.add(
            header,
            self.token_warning,
            ft.Row([
                self.repo_url_field,
                self.max_depth_field
            ]),
            ft.Container(
                content=ft.Text("無視パターン設定", weight=ft.FontWeight.BOLD),
                margin=ft.margin.only(top=20, bottom=10)
            ),
            ft.Row([
                ft.Column([
                    ft.Text("ファイル無視パターン"),
                    self.ignore_patterns_field
                ], expand=True),
                ft.Column([
                    ft.Text("ソースコード内無視パターン"),
                    self.source_ignore_patterns_field
                ], expand=True)
            ]),
            ft.Container(
                content=ft.Text("出力設定", weight=ft.FontWeight.BOLD),
                margin=ft.margin.only(top=20, bottom=10)
            ),
            ft.Row([
                self.format_dropdown,
                self.generate_button
            ]),
            self.progress_bar,
            self.progress_text,
            self.status_text,
            ft.Container(
                content=ft.Text("生成結果", weight=ft.FontWeight.BOLD),
                margin=ft.margin.only(top=20, bottom=10),
                visible=False,
                data="result_header"
            ),
            ft.Row([
                self.copy_button,
                self.download_button
            ], visible=False, data="result_buttons"),
            self.result_text
        )
    
    def update_status(self, message: str, is_error: bool = False):
        """
        ステータステキストを更新します。
        
        @param message - 表示するメッセージ
        @param is_error - エラーメッセージかどうか
        """
        self.status_text.value = message
        self.status_text.color = "red" if is_error else None
        self.page.update(self.status_text)
    
    def update_progress(self, message: str):
        """
        進捗テキストを更新します。
        
        @param message - 表示するメッセージ
        """
        self.progress_text.value = message
        self.progress_text.visible = True
        self.page.update(self.progress_text)
    
    def set_loading(self, loading: bool):
        """
        ローディング状態を設定します。
        
        @param loading - ローディング中かどうか
        """
        self.loading = loading
        self.progress_bar.visible = loading
        self.progress_text.visible = loading
        self.generate_button.disabled = loading
        
        self.page.update(
            self.progress_bar,
            self.progress_text,
            self.generate_button
        )
    
    def parse_patterns(self, text: str) -> List[str]:
        """
        テキストから無視パターンのリストを解析します。
        
        @param text - 無視パターンのテキスト
        @return 無視パターンのリスト
        """
        if not text:
            return []
        
        # 空行を除外
        return [line.strip() for line in text.split("\n") if line.strip()]
    
    async def generate_markdown(self, e):
        """
        マークダウンを生成します。
        
        @param e - イベントオブジェクト
        """
        # 入力検証
        repo_url = self.repo_url_field.value
        if not repo_url:
            self.update_status("リポジトリURLを入力してください。", True)
            return
        
        # 無視パターンの解析
        self.ignore_patterns = self.parse_patterns(self.ignore_patterns_field.value)
        self.source_ignore_patterns = self.parse_patterns(self.source_ignore_patterns_field.value)
        
        # 最大深度の解析
        try:
            max_depth = int(self.max_depth_field.value)
        except ValueError:
            max_depth = -1
            self.max_depth_field.value = "-1"
            self.page.update(self.max_depth_field)
        
        # 出力フォーマット
        output_format = self.format_dropdown.value
        
        # ローディング開始
        self.set_loading(True)
        self.update_status("リポジトリ情報を取得中...")
        
        try:
            # リポジトリ情報の解析
            self.update_progress("リポジトリURLを解析中...")
            repo_info = parseRepoUrl(repo_url)
            if not repo_info:
                self.update_status("無効なGitHub URLです。", True)
                self.set_loading(False)
                return
            
            # リポジトリ情報の取得
            self.update_status("リポジトリ情報を取得中...")
            self.update_progress(f"リポジトリ {repo_info['owner']}/{repo_info['repo']} のデフォルトブランチを取得中...")
            default_branch = await getDefaultBranch(repo_info)
            
            self.update_progress(f"リポジトリ {repo_info['owner']}/{repo_info['repo']} の詳細情報を取得中...")
            repo_details = await getRepositoryInfo(repo_url)
            
            # コントリビューター情報の取得
            self.update_status("コントリビューター情報を取得中...")
            self.update_progress(f"リポジトリ {repo_info['owner']}/{repo_info['repo']} のコントリビューター情報を取得中...")
            contributors = await getRepositoryContributors(repo_url, 10)
            
            # ファイルツリーの取得
            self.update_status("ファイルツリーを取得中...")
            self.update_progress(f"リポジトリ {repo_info['owner']}/{repo_info['repo']} のファイルツリーを取得中...")
            tree = await getRepoTree(repo_info, default_branch)
            
            # ファイルツリーの構築
            self.update_status("ファイルツリーを構築中...")
            self.update_progress(f"取得したファイル数: {len(tree)}、無視パターン: {len(self.ignore_patterns)}個")
            file_tree = buildFileTree(tree, self.ignore_patterns, max_depth)
            
            # マークダウンの生成
            self.update_status("マークダウンを生成中...")
            self.update_progress("リポジトリ情報からマークダウンを生成中...")
            markdown = await generateRepositoryMarkdown(
                repo_info,
                repo_details,
                contributors,
                file_tree,
                default_branch,
                self.ignore_patterns,
                self.source_ignore_patterns
            )
            
            # 結果の表示
            self.markdown_result = markdown
            
            # HTMLに変換
            if output_format == "html":
                self.update_progress("マークダウンをHTMLに変換中...")
                html = convertMarkdownToHtml(markdown)
                self.markdown_result = html
            
            # 結果表示
            self.update_progress("結果を表示中...")
            self.result_text.value = self.markdown_result
            self.result_text.visible = True
            
            # ボタンの有効化
            self.copy_button.disabled = False
            self.download_button.disabled = False
            
            # 結果セクションの表示
            for control in self.page.controls:
                if hasattr(control, "data") and control.data == "result_header":
                    control.visible = True
                elif hasattr(control, "data") and control.data == "result_buttons":
                    control.visible = True
            
            self.update_status("ドキュメントが正常に生成されました。")
            
            # トークンがない場合は警告を表示
            if not GITHUB_TOKEN:
                self.update_status("注意: GitHub API トークンが設定されていないため、一部の情報が制限されています。")
            
        except Exception as ex:
            error_msg = str(ex)
            self.update_status(f"エラーが発生しました: {error_msg}", True)
            print(f"詳細なエラー: {ex}")
            print(traceback.format_exc())  # スタックトレースを出力
            
            # NoneTypeエラーの場合は特別なメッセージを表示
            if "'NoneType' object has no attribute" in error_msg:
                self.update_status("エラー: データの取得に失敗しました。リポジトリURLを確認してください。", True)
        finally:
            self.set_loading(False)
            self.page.update()
    
    def copy_to_clipboard(self, e):
        """
        生成されたマークダウンをクリップボードにコピーします。
        
        @param e - イベントオブジェクト
        """
        try:
            self.page.set_clipboard(self.markdown_result)
            self.update_status("クリップボードにコピーしました。")
        except Exception as e:
            self.update_status(f"クリップボードへのコピーに失敗しました: {str(e)}", True)
    
    def download_markdown(self, e):
        """
        生成されたマークダウンをダウンロードします。
        
        @param e - イベントオブジェクト
        """
        # リポジトリ名を取得
        repo_url = self.repo_url_field.value
        repo_info = parseRepoUrl(repo_url)
        
        if repo_info:
            repo_name = repo_info["repo"]
        else:
            repo_name = "repository"
        
        # 出力フォーマット
        output_format = self.format_dropdown.value
        extension = ".html" if output_format == "html" else ".md"
        
        # ファイル名
        filename = f"{repo_name}_docs{extension}"
        
        try:
            # ダウンロード
            self.page.launch_url(
                self.page.get_upload_url(
                    self.markdown_result.encode("utf-8"),
                    file_name=filename
                )
            )
            
            self.update_status(f"{filename} をダウンロードしました。")
        except Exception as e:
            self.update_status(f"ダウンロード中にエラーが発生しました: {str(e)}", True)

def main(page: ft.Page):
    """
    メイン関数
    
    @param page - Flet ページオブジェクト
    """
    app = RepoSageApp(page)

# Hugging Face Spaces 用のエントリーポイント
if __name__ == "__main__":
    import sys
    
    def find_free_port():
        """
        使用可能なポートを見つけます。
        
        @return 使用可能なポート番号
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    # コマンドライン引数からポート番号を取得
    port = 8080
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass
        elif arg.startswith("--port="):
            try:
                port = int(arg.split("=")[1])
            except (ValueError, IndexError):
                pass
    
    # 環境変数からポートを取得（コマンドライン引数がない場合）
    if port == 8080 and "PORT" in os.environ:
        try:
            port = int(os.environ["PORT"])
        except ValueError:
            pass
    
    # 指定されたポートが使用中の場合は、空きポートを自動的に検出
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', port))
    except OSError:
        print(f"ポート {port} は既に使用されています。空きポートを検索します...")
        port = find_free_port()
    
    print(f"ポート {port} でアプリケーションを起動しています...")
    try:
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=port)
    except Exception as e:
        print(f"アプリケーションの起動中にエラーが発生しました: {str(e)}")
        # 再度空きポートを検索して試行
        try:
            new_port = find_free_port()
            print(f"別のポート {new_port} で再試行します...")
            ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=new_port)
        except Exception as e2:
            print(f"再試行中にもエラーが発生しました: {str(e2)}")
            sys.exit(1) 